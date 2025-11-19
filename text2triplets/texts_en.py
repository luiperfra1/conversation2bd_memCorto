# Various examples to test the extractor with different challenges

# Base case: symptom + medication with periodicity
TEXT1 = "user_jose suffers from insomnia. user_jose takes paracetamol every night."

# Activity + symptom with severity + frequency
TEXT2 = "user_maria walks daily. user_maria suffers from moderate lower back pain."

# Medication with indication + activity with frequency
TEXT3 = "user_carlos takes ibuprofen when it hurts. user_carlos practices yoga several times a week."

# Richer summary, multiple sentences and properties
TEXT4 = (
    "user_ana swims three times a week. "
    "user_ana suffers from moderate dizziness since 2023-01-15. "
    "user_ana takes ibuprofen when it hurts."
)

# Explicit negation (should not generate any medication triplets)
TEXT5 = "user_juan does not take any medication currently."

# Recommendation/hypothesis (should not generate medication)
TEXT6 = "The doctor recommended user_raul take ibuprofen if pain appears."

# Two people + social relationship + different activities
TEXT7 = (
    "user_luis has known user_marta for years. "
    "user_luis walks daily. "
    "user_marta practices yoga on weekends."
)

# Conversational noise, should extract the essentials
TEXT8 = (
    "user_elena suffers from insomnia. "
    "user_elena walks daily. "
    "user_elena takes valerian at night."
)

# Future plan (should not create activity)
TEXT9 = "user_sofia plans to start running next week."

# Ambiguous / allergy (may or may not be extracted depending on your ontology)
TEXT10 = "user_pedro is allergic to pollen. user_pedro sneezes sometimes."

# Multiple properties together
TEXT11 = (
    "user_miguel suffers from mild neck pain since 2025-09-10. "
    "user_miguel practices pilates daily. "
    "user_miguel takes naproxen every 8 hours when it hurts."
)

TEXT12 = "user_sara takes levothyroxine on an empty stomach every morning. user_sara practices pilates twice a week."

# Map for CLI or other tools
ALL_TEXTS = {
    "TEXT1": TEXT1,   # basic: symptom + medication
    "TEXT2": TEXT2,   # activity + symptom + severity
    "TEXT3": TEXT3,   # medication with indication + activity
    "TEXT4": TEXT4,   # rich summary with properties
    "TEXT5": TEXT5,   # negation
    "TEXT6": TEXT6,   # recommendation (hypothetical)
    "TEXT7": TEXT7,   # two people + social relationship
    "TEXT8": TEXT8,   # conversational noise
    "TEXT9": TEXT9,   # future plan
    "TEXT10": TEXT10, # allergy (outside ontology)
    "TEXT11": TEXT11, # multiple properties + frequency + periodicity
    "TEXT12": TEXT12, # multiple sentences with same person
}