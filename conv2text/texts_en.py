# conv2text/texts.py
"""
Collection of example conversations (compact and varied version).
Format: 'LLM:' and 'user_<name>:'.
Each entry tests a different type of behavior.
"""

ALL_TEXTS = {

    # === Simple base case: activity + medication + symptom ===
    "TEXT1": """LLM: What do you usually do in the mornings?
user_juan: I go running every day and take ibuprofen when I have a headache.
LLM: Do you notice any usual symptoms?
user_juan: Nothing serious, just some tiredness sometimes.
""",

    # === Activity + symptom with defined time ===
    "TEXT2": """LLM: How have you been lately?
user_marta: Since March 2024 I've had back pain, but I walk half an hour every afternoon.
""",

    # === Regular medication and habitual exercise ===
    "TEXT3": """LLM: What's your daily routine?
user_pedro: I go to the gym three times a week and take metformin every morning.
""",

    # === Persistent symptom + relaxing activity ===
    "TEXT4": """LLM: Do you sleep well?
user_lucia: I've had insomnia for two months.
LLM: Do you do any physical activity?
user_lucia: I do yoga on weekends to relax.
""",

    # === Ambiguous case: medical recommendation, no real action ===
    "TEXT5": """LLM: Are you taking any medication?
user_eduardo: The doctor told me to start amoxicillin if the sore throat returns, but I'm not taking it now.
""",

    # === Complete denial case (no useful information) ===
    "TEXT6": """LLM: Do you have any symptoms or take medication?
user_javier: I have no symptoms and I'm not taking anything right now.
""",

    # === Case with past + present (time mix) ===
    "TEXT7": """LLM: How are you feeling today?
user_laura: I had a fever yesterday, but I'm fine today. I took ibuprofen and rested. I usually do pilates on Tuesdays and Thursdays.
""",

    # === Case of interrupted habits (suspended activity) ===
    "TEXT8": """LLM: Have you been exercising lately?
user_ines: I used to go to the gym, but I stopped because I'm traveling. I sometimes take vitamin D when I remember.
""",

    # === Emotional/psychological case ===
    "TEXT9": """LLM: How have you been feeling lately?
user_sandra: I'm a bit nervous and sleeping poorly. I do yoga in the mornings and take lorazepam at night for a month now.
""",

    # === Mixed case with diagnosed illness ===
    "TEXT10": """LLM: Tell me about your daily life.
user_pablo: I work from home and use the stationary bike in the mornings. I've been type 2 diabetic for 5 years and take metformin twice a day.
""",

    # === Long and varied case: combines symptoms, emotions and routines ===
    "TEXT11": """LLM: Tell me about your recent weeks.
user_clara: They've been somewhat heavy. I've had mild neck pain for months, especially at the end of the day. 
I go swimming on Saturdays, walk almost every day and practice some meditation before sleeping. 
I take simvastatin every night because I have high cholesterol, and my doctor told me to watch my diet. 
Sometimes I have trouble sleeping due to stress, but I try not to worry too much. 
LLM: Do you notice any improvement with exercise?
user_clara: Yes, when I exercise I feel better, although the pain returns if I spend too much time at the computer.
""",

    # === Case without relevant information (conversational noise) ===
    "TEXT12": """LLM: How was your weekend?
user_david: Good, I was with my family and we watched a movie. I haven't done anything special.
LLM: And health-wise?
user_david: Everything normal, nothing new to report.
""",

    # === Negative-conditional case (hypothetical) ===
    "TEXT13": """LLM: Did the doctor prescribe you anything?
user_rocio: He said I could take paracetamol if the pain returned, but I haven't needed it.
""",

    # === Mild physical case + social activity ===
    "TEXT14": """LLM: How's your health lately?
user_maria: Good, just mild nasal congestion from allergies. I walk with my daughter every afternoon and go to pilates on Saturdays.
""",

    # === Prolonged emotional case + constant treatment ===
    "TEXT15": """LLM: How have you been these days?
user_ernesto: I've been sleeping poorly for weeks with lots of anxiety. 
I try to relax by listening to music and do stretches in the afternoon. 
I've been taking lorazepam for three months.
""",

    # === Extensive and detailed case: symptoms, emotions, routines and medical follow-up ===
"TEXT16": """LLM: How have you been these days?
user_ernesto: I've been sleeping poorly for weeks with lots of anxiety. I wake up several times during the night, especially when I have work worries. 
I try to relax by listening to music before sleeping, but sometimes it doesn't work. I also do stretches in the afternoon and walk about twenty minutes after dinner. 
I've been taking lorazepam for three months because the doctor prescribed it for my anxiety. It generally helps, although lately I notice the effect doesn't last as long.

LLM: Have you noticed any other physical symptoms?
user_ernesto: Yes, neck pain and some tension in my shoulders, especially when I spend a lot of time at the computer. Sometimes I get mild tachycardia, but it goes away when I breathe deeply. 
I don't have fever or anything more serious.

LLM: Do you follow any exercise or eating routines?
user_ernesto: I try to eat healthy during the week, although on weekends I usually eat out. I practice yoga once a week and sometimes go biking with a friend on Sundays, but not always. 
I've thought about joining swimming, although I have trouble organizing myself.

LLM: Has your sleep improved or is it the same?
user_ernesto: A bit better than at the beginning, but I still wake up at least two or three times every night. When I rest well, I feel calmer the next day. 
I also notice that if I take the lorazepam too late, I wake up somewhat dizzy.

LLM: Have you talked about this with your doctor recently?
user_ernesto: Yes, two weeks ago. He recommended keeping fixed sleep schedules, reducing coffee and avoiding screens at night. He said if I don't improve, we could change the dose or try another medication.

LLM: I understand. Do you want to add anything else?
user_ernesto: Just that I'd like to sleep better without depending on medication. I'm trying to be consistent with routines, although some days it's hard. 
When I manage to sleep well and stay active, my mood improves a lot.
""",

 "TEXT17": """LLM: How old are you?
user_ernesto: I'm 45 years old
""",
 "TEXT18": """LLM: What are you doing?
user_ernesto: Well, I was calling María to see if she wanted to go running with me this afternoon.
""",
 "TEXT19": """LLM: What are you doing?
user_ernesto: Well, I was calling Ernesto to see if he wanted to go running with me this afternoon.
""",
}