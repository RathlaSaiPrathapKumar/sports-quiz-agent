import json
import random
from openai import OpenAI
from google import genai
from google.genai import types
from src.config import OPENAI_API_KEY, GEMINI_API_KEY
from src.database import query_historic_facts
from src.search import get_live_news_context

def compile_quiz_data(sport, difficulty, num_questions=6, provider=None):
    """
    1. Gathers context from ChromaDB (Historical).
    2. Gathers context from DuckDuckGo (Live news).
    3. Blends them inside a grounded prompt.
    4. Connects to OpenAI/Gemini to generate a structured JSON quiz.
    5. Falls back to mock data if keys are missing or API calls fail.
    """
    # 1. Retrieve historical facts from ChromaDB
    db_query = f"{sport} history cup championships rules records"
    db_matches = query_historic_facts(sport=sport, query_text=db_query, n_results=2)
    db_context = "\n".join(db_matches) if db_matches else "No offline historic data recorded."

    # 2. Retrieve live match results from web search
    web_context = get_live_news_context(sport)

    # 3. Combine context
    unified_context = f"=== HISTORICAL FACTS ===\n{db_context}\n\n=== LIVE INTERNET NEWS ===\n{web_context}"

    # Determine which LLM provider to use
    if not provider:
        if GEMINI_API_KEY:
            provider = "Gemini"
        elif OPENAI_API_KEY:
            provider = "OpenAI"
        else:
            provider = "Mock"

    # Define strict system instructions for the LLM
    system_instruction = (
        "You are an expert sports quiz creator. Your job is to write a multiple-choice quiz "
        "relying strictly on the provided Context. Avoid hallucinations. Do not use facts not "
        "found in the Context below. If facts are scarce, make do with what you have, "
        "but keep details completely accurate to the text context. "
        "To provide variety, randomize the focus of your questions (e.g. player achievements, match history, dates, rules) "
        "and do not repeat questions from previous runs. "
        "You must respond ONLY with a valid JSON object matching the requested schema. No extra text."
    )

    user_prompt = (
        f"Generate exactly {num_questions} unique, distinct, and highly creative multiple-choice questions for the sport: {sport}.\n"
        f"Difficulty target: {difficulty}.\n"
        "Make sure the questions cover varied aspects (player records, match outcomes, rules, tournament history) so that every generated quiz feels completely fresh and distinct from previous runs.\n\n"
        "CONTEXT DETAILS:\n"
        f"{unified_context}\n\n"
        "Format the output strictly as a JSON object with a single root key 'quiz', containing a list of questions. "
        "Each question object must contain the following keys exactly:\n"
        "- 'question': The question string\n"
        "- 'options': An object with options 'A', 'B', 'C', 'D' as keys\n"
        "- 'correct_answer': A single string 'A', 'B', 'C', or 'D'\n"
        "- 'explanation': A detailed explanation of why the answer is correct, referencing facts from the Context.\n\n"
        "Example JSON output shape:\n"
        "{\n"
        "  \"quiz\": [\n"
        "    {\n"
        "      \"question\": \"Question text here?\",\n"
        "      \"options\": {\n"
        "        \"A\": \"Option A text\",\n"
        "        \"B\": \"Option B text\",\n"
        "        \"C\": \"Option C text\",\n"
        "        \"D\": \"Option D text\"\n"
        "      },\n"
        "      \"correct_answer\": \"A\",\n"
        "      \"explanation\": \"Grounded explanation quoting from the context...\"\n"
        "    }\n"
        "  ]\n"
        "}"
    )

    # 4. Generate using the selected provider
    if provider == "OpenAI" and OPENAI_API_KEY:
        try:
            print("[INFO]: Generating quiz using OpenAI API...")
            client = OpenAI(api_key=OPENAI_API_KEY)
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",  # fallback or modern default (e.g. gpt-4o-mini)
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.85
            )
            quiz_json_str = response.choices[0].message.content
            quiz_data = json.loads(quiz_json_str)
            return quiz_data, unified_context, "OpenAI"
        except Exception as e:
            print(f"[ERROR]: OpenAI quiz generation failed: {e}. Falling back to mock data.")
            # Fall through to mock data if OpenAI fails

    elif provider == "Gemini" and GEMINI_API_KEY:
        try:
            print("[INFO]: Generating quiz using Google Gemini API...")
            client = genai.Client(api_key=GEMINI_API_KEY)
            # Use gemini-1.5-flash as the fast default
            response = client.models.generate_content(
                model='gemini-1.5-flash',
                contents=f"{system_instruction}\n\n{user_prompt}",
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.85
                )
            )
            quiz_json_str = response.text
            quiz_data = json.loads(quiz_json_str)
            return quiz_data, unified_context, "Gemini"
        except Exception as e:
            print(f"[ERROR]: Gemini quiz generation failed: {e}. Falling back to mock data.")
            # Fall through to mock data if Gemini fails

    # 5. Mock / Fallback generator if API keys are missing or calls fail
    print("[INFO]: Using mock generator (either keys are missing or API calls failed).")
    mock_quiz = get_mock_quiz(sport, difficulty, num_questions)
    mock_context = (
        f"=== HISTORICAL FACTS ===\n[MOCK CONTEXT] Loaded fallback facts for {sport}.\n\n"
        f"=== LIVE INTERNET NEWS ===\n[MOCK CONTEXT] DuckDuckGo crawler skipped/offline."
    )
    return mock_quiz, mock_context, "Mock (No API keys provided or error occurred)"


def get_mock_quiz(sport, difficulty, num_questions=6):
    """
    Returns a randomized, pre-compiled, structured sports quiz so the app remains fully functional without keys.
    """
    mock_db = {
        "Cricket": {
            "Easy": {
                "quiz": [
                    {
                        "question": "When was the first official cricket Test match played?",
                        "options": {"A": "1901", "B": "1877", "C": "1882", "D": "1923"},
                        "correct_answer": "B",
                        "explanation": "The first official cricket Test match was played in 1877 between Australia and England at the Melbourne Cricket Ground (MCG). Australia won by 45 runs."
                    },
                    {
                        "question": "Which country won the first two ICC Cricket World Cups?",
                        "options": {"A": "West Indies", "B": "Australia", "C": "England", "D": "India"},
                        "correct_answer": "A",
                        "explanation": "The West Indies won the first two ICC Cricket World Cups in 1975 and 1979 under the captaincy of Clive Lloyd."
                    },
                    {
                        "question": "Where is the Melbourne Cricket Ground (MCG) located?",
                        "options": {"A": "New Zealand", "B": "England", "C": "Australia", "D": "South Africa"},
                        "correct_answer": "C",
                        "explanation": "The Melbourne Cricket Ground (MCG) is in Melbourne, Australia, and hosted the inaugural Test match in 1877."
                    },
                    {
                        "question": "Which country won the ICC Cricket World Cup in 1983?",
                        "options": {"A": "West Indies", "B": "England", "C": "India", "D": "Australia"},
                        "correct_answer": "C",
                        "explanation": "India won its first historic ICC Cricket World Cup in 1983 under the captaincy of Kapil Dev."
                    },
                    {
                        "question": "What is the maximum number of players allowed on the field for a fielding team in cricket?",
                        "options": {"A": "10", "B": "11", "C": "12", "D": "9"},
                        "correct_answer": "B",
                        "explanation": "In cricket, the fielding side has 11 players on the field at any one time."
                    },
                    {
                        "question": "How many balls are in a standard over in cricket?",
                        "options": {"A": "4", "B": "5", "C": "6", "D": "8"},
                        "correct_answer": "C",
                        "explanation": "A standard cricket over consists of exactly six legal deliveries bowled by the bowler."
                    }
                ]
            },
            "Medium": {
                "quiz": [
                    {
                        "question": "Who captained the West Indies team to victories in the first two Cricket World Cups?",
                        "options": {"A": "Viv Richards", "B": "Garfield Sobers", "C": "Clive Lloyd", "D": "Malcolm Marshall"},
                        "correct_answer": "C",
                        "explanation": "Clive Lloyd captained the West Indies team during their victorious 1975 and 1979 ICC World Cup campaigns."
                    },
                    {
                        "question": "How many international centuries did Sachin Tendulkar score in ODIs?",
                        "options": {"A": "51", "B": "49", "C": "100", "D": "39"},
                        "correct_answer": "B",
                        "explanation": "Sachin Tendulkar scored a total of 100 international centuries, of which 49 were in ODIs and 51 in Test cricket."
                    },
                    {
                        "question": "By how many runs did Australia win the historic first Test match in 1877?",
                        "options": {"A": "10 runs", "B": "45 runs", "C": "82 runs", "D": "120 runs"},
                        "correct_answer": "B",
                        "explanation": "Australia won the first official Test match in 1877 at the MCG by exactly 45 runs, defeating England."
                    },
                    {
                        "question": "Which player holds the record for the highest individual score in a Test match (400 not out)?",
                        "options": {"A": "Sachin Tendulkar", "B": "Brian Lara", "C": "Don Bradman", "D": "Chris Gayle"},
                        "correct_answer": "B",
                        "explanation": "Brian Lara of the West Indies holds the record for the highest individual Test score, scoring 400 not out against England in 2004."
                    },
                    {
                        "question": "What is the standard length of a cricket pitch between the wickets?",
                        "options": {"A": "20 yards", "B": "22 yards", "C": "24 yards", "D": "18 yards"},
                        "correct_answer": "B",
                        "explanation": "A standard cricket pitch measures exactly 22 yards (20.12 meters) from wicket to wicket."
                    },
                    {
                        "question": "Which country won the ICC Men's T20 World Cup held in 2024?",
                        "options": {"A": "South Africa", "B": "India", "C": "Australia", "D": "England"},
                        "correct_answer": "B",
                        "explanation": "India won the 2024 ICC Men's T20 World Cup by defeating South Africa in a thrilling final match."
                    }
                ]
            },
            "Hard": {
                "quiz": [
                    {
                        "question": "At which venue were the first two Cricket World Cup finals held?",
                        "options": {"A": "The Oval", "B": "Melbourne Cricket Ground", "C": "Lord's in London", "D": "Eden Gardens"},
                        "correct_answer": "C",
                        "explanation": "Both of the first two Cricket World Cup finals in 1975 and 1979 were played at Lord's Cricket Ground in London."
                    },
                    {
                        "question": "In what year did Sachin Tendulkar retire from international cricket?",
                        "options": {"A": "2011", "B": "2013", "C": "2015", "D": "2010"},
                        "correct_answer": "B",
                        "explanation": "Sachin Tendulkar retired from international cricket in the year 2013 after scoring 100 international centuries."
                    },
                    {
                        "question": "Who was Australia's opponent in the first ever official Test Match of 1877?",
                        "options": {"A": "South Africa", "B": "West Indies", "C": "England", "D": "New Zealand"},
                        "correct_answer": "C",
                        "explanation": "The first official cricket Test match was played between Australia and England in 1877."
                    },
                    {
                        "question": "Which bowler has taken the most wickets in Test cricket history?",
                        "options": {"A": "Shane Warne", "B": "Muttiah Muralitharan", "C": "James Anderson", "D": "Anil Kumble"},
                        "correct_answer": "B",
                        "explanation": "Muttiah Muralitharan of Sri Lanka holds the record for the most Test wickets in history, claiming 800 wickets."
                    },
                    {
                        "question": "In cricket, what does the term 'Maiden Over' refer to?",
                        "options": {
                            "A": "The first over of a match",
                            "B": "An over in which no runs are scored off the bat",
                            "C": "An over in which a bowler takes three wickets",
                            "D": "The final over of a match"
                        },
                        "correct_answer": "B",
                        "explanation": "A maiden over is an over in which the bowler delivers six balls without the batting team scoring any runs."
                    },
                    {
                        "question": "Who captained India to their historic first Cricket World Cup win in 1983?",
                        "options": {"A": "Sunil Gavaskar", "B": "Kapil Dev", "C": "Ravi Shastri", "D": "Dilip Vengsarkar"},
                        "correct_answer": "B",
                        "explanation": "Kapil Dev captained the Indian cricket team that won the 1983 World Cup by defeating West Indies in the final."
                    }
                ]
            }
        },
        "Football": {
            "Easy": {
                "quiz": [
                    {
                        "question": "Which country hosted and won the first-ever FIFA World Cup in 1930?",
                        "options": {"A": "Argentina", "B": "Brazil", "C": "Uruguay", "D": "Italy"},
                        "correct_answer": "C",
                        "explanation": "The first FIFA World Cup was held in 1930. Uruguay hosted and won the tournament, defeating Argentina 4-2 in the final."
                    },
                    {
                        "question": "Who is the only player in football history to win three FIFA World Cups?",
                        "options": {"A": "Diego Maradona", "B": "Lionel Messi", "C": "Pelé", "D": "Zinedine Zidane"},
                        "correct_answer": "C",
                        "explanation": "Pelé of Brazil is the only player in football history to win three FIFA World Cup titles as a player, claiming victories in 1958, 1962, and 1970."
                    },
                    {
                        "question": "Which team did Argentina defeat to win the 2022 FIFA World Cup in Qatar?",
                        "options": {"A": "Croatia", "B": "France", "C": "Morocco", "D": "Brazil"},
                        "correct_answer": "B",
                        "explanation": "In the 2022 FIFA World Cup held in Qatar, Argentina won their third World Cup title by defeating France 4-2 on penalties."
                    },
                    {
                        "question": "How many players from each team are on the field at the start of a standard football match?",
                        "options": {"A": "10", "B": "11", "C": "12", "D": "9"},
                        "correct_answer": "B",
                        "explanation": "A standard football match is played by two teams, each consisting of 11 active players including the goalkeeper."
                    },
                    {
                        "question": "How long is a standard professional football match, excluding extra time?",
                        "options": {"A": "80 minutes", "B": "90 minutes", "C": "100 minutes", "D": "60 minutes"},
                        "correct_answer": "B",
                        "explanation": "A professional football match is split into two halves of 45 minutes each, totaling 90 minutes of standard play time."
                    },
                    {
                        "question": "Which nation has won the most FIFA World Cup titles in history?",
                        "options": {"A": "Germany", "B": "Italy", "C": "Brazil", "D": "Argentina"},
                        "correct_answer": "C",
                        "explanation": "Brazil is the most successful nation in FIFA World Cup history, having won the tournament five times."
                    }
                ]
            },
            "Medium": {
                "quiz": [
                    {
                        "question": "What was the final score of the 1930 FIFA World Cup final in Montevideo?",
                        "options": {"A": "Uruguay 2-1 Argentina", "B": "Uruguay 4-2 Argentina", "C": "Uruguay 3-2 Argentina", "D": "Uruguay 1-0 Argentina"},
                        "correct_answer": "B",
                        "explanation": "Uruguay hosted and won the first FIFA World Cup in 1930, defeating Argentina 4-2 in the final match in Montevideo."
                    },
                    {
                        "question": "In which years did Pelé win his three FIFA World Cups?",
                        "options": {"A": "1958, 1962, 1966", "B": "1954, 1958, 1962", "C": "1958, 1962, 1970", "D": "1962, 1966, 1970"},
                        "correct_answer": "C",
                        "explanation": "Pelé won three World Cup championships in 1958, 1962, and 1970."
                    },
                    {
                        "question": "How did Argentina win the 2022 World Cup after the extra time ended in a 3-3 draw?",
                        "options": {"A": "Golden Goal", "B": "Coin Toss", "C": "4-2 on penalties", "D": "5-3 on penalties"},
                        "correct_answer": "C",
                        "explanation": "Argentina defeated France 4-2 on penalties after the match ended in a dramatic 3-3 draw in extra time."
                    },
                    {
                        "question": "Which European country won the UEFA Euro 2024 championship?",
                        "options": {"A": "England", "B": "France", "C": "Spain", "D": "Germany"},
                        "correct_answer": "C",
                        "explanation": "Spain won the UEFA Euro 2024 tournament, defeating England 2-1 in the final match."
                    },
                    {
                        "question": "Which football club has won the most UEFA Champions League titles?",
                        "options": {"A": "FC Barcelona", "B": "Real Madrid", "C": "AC Milan", "D": "Bayern Munich"},
                        "correct_answer": "B",
                        "explanation": "Real Madrid is historically the most successful club in the UEFA Champions League, holding the record for the most trophies."
                    },
                    {
                        "question": "What is the official distance of a penalty kick from the goal line in football?",
                        "options": {"A": "10 yards", "B": "12 yards", "C": "15 yards", "D": "8 yards"},
                        "correct_answer": "B",
                        "explanation": "The penalty spot is located exactly 12 yards (11 meters) from the center of the goal line."
                    }
                ]
            },
            "Hard": {
                "quiz": [
                    {
                        "question": "Where was the final match of the first-ever 1930 FIFA World Cup played?",
                        "options": {"A": "Buenos Aires", "B": "Montevideo", "C": "Rio de Janeiro", "D": "São Paulo"},
                        "correct_answer": "B",
                        "explanation": "The first FIFA World Cup final was played in Montevideo, Uruguay, in 1930."
                    },
                    {
                        "question": "How many World Cup titles does Argentina hold after the 2022 edition?",
                        "options": {"A": "Two", "B": "Three", "C": "Four", "D": "Five"},
                        "correct_answer": "B",
                        "explanation": "With their victory in Qatar in 2022, Argentina claimed their third FIFA World Cup title."
                    },
                    {
                        "question": "Which player is the unique record holder for winning three FIFA World Cups as an active footballer?",
                        "options": {"A": "Mário Zagallo", "B": "Franz Beckenbauer", "C": "Pelé", "D": "Ronaldo Nazário"},
                        "correct_answer": "C",
                        "explanation": "Pelé of Brazil is the only player in football history to win three FIFA World Cup titles as a player."
                    },
                    {
                        "question": "Which country won the inaugural UEFA European Championship (Euro) in 1960?",
                        "options": {"A": "Soviet Union", "B": "Yugoslavia", "C": "Spain", "D": "France"},
                        "correct_answer": "A",
                        "explanation": "The Soviet Union won the first-ever UEFA European Championship in 1960, defeating Yugoslavia 2-1 in extra time."
                    },
                    {
                        "question": "Which player scored the controversial 'Hand of God' goal in the 1986 World Cup?",
                        "options": {"A": "Pelé", "B": "Diego Maradona", "C": "Lionel Messi", "D": "Michel Platini"},
                        "correct_answer": "B",
                        "explanation": "Diego Maradona scored the famous 'Hand of God' goal against England in the quarter-finals of the 1986 World Cup."
                    },
                    {
                        "question": "In which year was the first FIFA Women's World Cup tournament held?",
                        "options": {"A": "1991", "B": "1995", "C": "1988", "D": "2003"},
                        "correct_answer": "A",
                        "explanation": "The first-ever FIFA Women's World Cup was hosted by China in the year 1991, won by the United States."
                    }
                ]
            }
        },
        "Badminton": {
            "Easy": {
                "quiz": [
                    {
                        "question": "In which year was the premier international men's team badminton tournament, the Thomas Cup, established?",
                        "options": {"A": "1992", "B": "1948", "C": "1955", "D": "1972"},
                        "correct_answer": "B",
                        "explanation": "The Thomas Cup, established in 1948, is the premier international men's team badminton championship."
                    },
                    {
                        "question": "Which nation won its historic first Thomas Cup title in 2022 by defeating Indonesia?",
                        "options": {"A": "Malaysia", "B": "India", "C": "China", "D": "Denmark"},
                        "correct_answer": "B",
                        "explanation": "India won its historic first title in 2022 by defeating Indonesia 3-0 in the final."
                    },
                    {
                        "question": "Where did badminton make its official Olympic debut as a medal sport?",
                        "options": {"A": "Seoul 1988", "B": "Barcelona 1992", "C": "Atlanta 1996", "D": "Tokyo 2020"},
                        "correct_answer": "B",
                        "explanation": "Badminton made its official Olympic debut as a medal sport at the 1992 Summer Games in Barcelona, Spain."
                    }
                ]
            },
            "Medium": {
                "quiz": [
                    {
                        "question": "What was the final score by which India defeated Indonesia in the 2022 Thomas Cup?",
                        "options": {"A": "3-2", "B": "3-0", "C": "3-1", "D": "2-1"},
                        "correct_answer": "B",
                        "explanation": "India defeated Indonesia 3-0 in the final match of the 2022 Thomas Cup to win its first title."
                    },
                    {
                        "question": "Who won the first-ever Olympic gold medal in badminton women's singles in 1992?",
                        "options": {"A": "Susi Susanti", "B": "Bang Soo-hyun", "C": "Carolina Marin", "D": "Zhang Ning"},
                        "correct_answer": "A",
                        "explanation": "Indonesia's Susi Susanti won the first-ever women's singles gold medal at the Barcelona 1992 Summer Games."
                    },
                    {
                        "question": "In which city did badminton debut as a medal event in the Olympic Games?",
                        "options": {"A": "Atlanta", "B": "Barcelona", "C": "Athens", "D": "Sydney"},
                        "correct_answer": "B",
                        "explanation": "Badminton debuted as an Olympic medal sport at the 1992 Games in Barcelona, Spain."
                    }
                ]
            },
            "Hard": {
                "quiz": [
                    {
                        "question": "Which country won the most Thomas Cup titles before being defeated by India in the 2022 final?",
                        "options": {"A": "China", "B": "Indonesia", "C": "Japan", "D": "Denmark"},
                        "correct_answer": "B",
                        "explanation": "Indonesia, the runner-up of the 2022 Thomas Cup, is historically the most successful country in this tournament, but was defeated 3-0 by India."
                    },
                    {
                        "question": "From which country is Susi Susanti, the first women's badminton Olympic gold medalist?",
                        "options": {"A": "Indonesia", "B": "China", "C": "South Korea", "D": "Malaysia"},
                        "correct_answer": "A",
                        "explanation": "Susi Susanti, who won the first-ever badminton women's singles gold medal in 1992, is from Indonesia."
                    },
                    {
                        "question": "In what year did India win its historic first Thomas Cup title?",
                        "options": {"A": "2020", "B": "2022", "C": "2021", "D": "2019"},
                        "correct_answer": "B",
                        "explanation": "India won its historic first Thomas Cup title in 2022."
                    }
                ]
            }
        }
    }

    # Handle fallback if sport or difficulty is not found
    sport_key = sport if sport in mock_db else "Cricket"
    diff_key = difficulty if difficulty in mock_db[sport_key] else "Easy"
    
    questions_pool = mock_db[sport_key][diff_key]["quiz"]
    
    # Randomly select requested number of unique questions from the pool
    # If pool is smaller than requested, sample with replacement or cycle
    if len(questions_pool) >= num_questions:
        selected_questions = random.sample(questions_pool, num_questions)
    else:
        # Cycle through to pad
        selected_questions = []
        for i in range(num_questions):
            selected_questions.append(questions_pool[i % len(questions_pool)])
    
    return {"quiz": selected_questions}
