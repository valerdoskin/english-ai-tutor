"""
question_bank.py — банк вопросов для адаптивного теста уровня CEFR.

Содержит статические вопросы для всех уровней (A1–C2).
Каждый вопрос имеет тип (grammar/vocabulary) для детального отчёта по навыкам.
"""

# Банк вопросов по уровням
# Каждый вопрос: {question, options, answer, level, skill}
QUESTION_BANK = {
    "A1": [
        # --- Грамматика ---
        {"question": "Choose the correct sentence:", "options": ["She go to school.", "She goes to school.", "She going to school.", "She gone to school."], "answer": 1, "skill": "grammar"},
        {"question": "Complete: 'I ___ a book right now.'", "options": ["read", "am reading", "reads", "reading"], "answer": 1, "skill": "grammar"},
        {"question": "What is the plural of 'child'?", "options": ["childs", "children", "childes", "childrens"], "answer": 1, "skill": "grammar"},
        {"question": "Complete: 'She ___ to work every day.'", "options": ["go", "goes", "going", "gone"], "answer": 1, "skill": "grammar"},
        {"question": "Choose the correct form: 'There ___ a book on the table.'", "options": ["is", "are", "am", "be"], "answer": 0, "skill": "grammar"},
        {"question": "Complete: 'I ___ a student.'", "options": ["am", "is", "are", "be"], "answer": 0, "skill": "grammar"},
        {"question": "Choose the correct sentence:", "options": ["He don't like coffee.", "He doesn't like coffee.", "He not like coffee.", "He doesn't likes coffee."], "answer": 1, "skill": "grammar"},
        {"question": "Complete: 'They ___ playing football now.'", "options": ["is", "are", "am", "be"], "answer": 1, "skill": "grammar"},
        {"question": "Choose the correct form: 'This is ___ apple.'", "options": ["a", "an", "the", "—"], "answer": 1, "skill": "grammar"},
        {"question": "Complete: 'I ___ my homework yesterday.'", "options": ["do", "did", "done", "does"], "answer": 1, "skill": "grammar"},
        # --- Лексика ---
        {"question": "What is the opposite of 'big'?", "options": ["large", "small", "tall", "wide"], "answer": 1, "skill": "vocabulary"},
        {"question": "Choose the correct word: 'I ___ my teeth every morning.'", "options": ["wash", "brush", "clean", "comb"], "answer": 1, "skill": "vocabulary"},
        {"question": "What is this? 'It's a ___ for drinking coffee.'", "options": ["plate", "cup", "bowl", "glass"], "answer": 1, "skill": "vocabulary"},
        {"question": "Choose the correct word: 'The ___ is shining today.'", "options": ["rain", "sun", "snow", "wind"], "answer": 1, "skill": "vocabulary"},
        {"question": "What is the opposite of 'hot'?", "options": ["warm", "cold", "cool", "freezing"], "answer": 1, "skill": "vocabulary"},
        {"question": "Choose the correct word: 'I need to buy some ___ at the supermarket.'", "options": ["food", "book", "pen", "shirt"], "answer": 0, "skill": "vocabulary"},
        {"question": "What is this? 'It's a ___ for writing.'", "options": ["book", "pen", "paper", "pencil"], "answer": 1, "skill": "vocabulary"},
        {"question": "Choose the correct word: 'My ___ is my mother's sister.'", "options": ["aunt", "uncle", "cousin", "grandmother"], "answer": 0, "skill": "vocabulary"},
        {"question": "What is the opposite of 'happy'?", "options": ["glad", "sad", "angry", "tired"], "answer": 1, "skill": "vocabulary"},
        {"question": "Choose the correct word: 'I ___ to music every evening.'", "options": ["listen", "hear", "watch", "look"], "answer": 0, "skill": "vocabulary"},
    ],
    "A2": [
        # --- Грамматика ---
        {"question": "Choose the correct form: 'If it rains, we ___ at home.'", "options": ["stay", "will stay", "stayed", "would stay"], "answer": 1, "skill": "grammar"},
        {"question": "Complete: 'She has lived here ___ 2010.'", "options": ["for", "since", "from", "during"], "answer": 1, "skill": "grammar"},
        {"question": "Choose the correct sentence:", "options": ["I am agree with you.", "I agree with you.", "I agreeing with you.", "I agreed with you."], "answer": 1, "skill": "grammar"},
        {"question": "Complete: 'I ___ to the cinema last night.'", "options": ["go", "went", "gone", "going"], "answer": 1, "skill": "grammar"},
        {"question": "Choose the correct form: 'She is ___ than her sister.'", "options": ["tall", "taller", "tallest", "more tall"], "answer": 1, "skill": "grammar"},
        {"question": "Complete: 'We ___ been to Paris twice.'", "options": ["has", "have", "had", "having"], "answer": 1, "skill": "grammar"},
        {"question": "Choose the correct sentence:", "options": ["I have been working here since 5 years.", "I have been working here for 5 years.", "I am working here since 5 years.", "I work here since 5 years."], "answer": 1, "skill": "grammar"},
        {"question": "Complete: '___ you like some tea?'", "options": ["Do", "Would", "Will", "Can"], "answer": 1, "skill": "grammar"},
        {"question": "Choose the correct form: 'This is the ___ book I've ever read.'", "options": ["good", "better", "best", "well"], "answer": 2, "skill": "grammar"},
        {"question": "Complete: 'I'm going to ___ my friend tomorrow.'", "options": ["visit", "visiting", "visited", "visits"], "answer": 0, "skill": "grammar"},
        # --- Лексика ---
        {"question": "Choose the correct word: 'I need to ___ a doctor.'", "options": ["see", "look", "watch", "view"], "answer": 0, "skill": "vocabulary"},
        {"question": "What is the opposite of 'expensive'?", "options": ["cheap", "costly", "pricey", "dear"], "answer": 0, "skill": "vocabulary"},
        {"question": "Choose the correct word: 'She ___ a new dress yesterday.'", "options": ["bought", "buyed", "buys", "buying"], "answer": 0, "skill": "vocabulary"},
        {"question": "What does 'delicious' mean?", "options": ["very tasty", "very big", "very fast", "very old"], "answer": 0, "skill": "vocabulary"},
        {"question": "Choose the correct word: 'I'm ___ because I didn't sleep well.'", "options": ["tired", "happy", "excited", "angry"], "answer": 0, "skill": "vocabulary"},
        {"question": "What is the opposite of 'early'?", "options": ["late", "soon", "quick", "fast"], "answer": 0, "skill": "vocabulary"},
        {"question": "Choose the correct word: 'We went on a ___ to the mountains.'", "options": ["trip", "travel", "journey", "voyage"], "answer": 0, "skill": "vocabulary"},
        {"question": "What does 'borrow' mean?", "options": ["to take something and return it", "to give something away", "to buy something", "to sell something"], "answer": 0, "skill": "vocabulary"},
        {"question": "Choose the correct word: 'The weather is ___ today, let's go outside.'", "options": ["nice", "bad", "terrible", "awful"], "answer": 0, "skill": "vocabulary"},
        {"question": "What is the opposite of 'difficult'?", "options": ["easy", "hard", "tough", "challenging"], "answer": 0, "skill": "vocabulary"},
    ],
    "B1": [
        # --- Грамматика ---
        {"question": "Choose the correct sentence:", "options": ["He suggested me to go.", "He suggested that I go.", "He suggested me going.", "He suggested to go."], "answer": 1, "skill": "grammar"},
        {"question": "Complete: 'By the time we arrived, the movie ___ .'", "options": ["started", "had started", "has started", "was starting"], "answer": 1, "skill": "grammar"},
        {"question": "Choose the correct form: 'I'm looking forward ___ you.'", "options": ["to see", "to seeing", "seeing", "see"], "answer": 1, "skill": "grammar"},
        {"question": "Complete: 'If I ___ you, I would study more.'", "options": ["am", "were", "was", "be"], "answer": 1, "skill": "grammar"},
        {"question": "Choose the correct sentence:", "options": ["She told me that she will come.", "She told me that she would come.", "She told me that she comes.", "She told me that she came."], "answer": 1, "skill": "grammar"},
        {"question": "Complete: 'The house ___ built in 1990.'", "options": ["was", "is", "has", "had"], "answer": 0, "skill": "grammar"},
        {"question": "Choose the correct form: 'I've been working here ___ 5 years.'", "options": ["since", "for", "during", "from"], "answer": 1, "skill": "grammar"},
        {"question": "Complete: 'She asked me where I ___ .'", "options": ["live", "lived", "living", "lives"], "answer": 1, "skill": "grammar"},
        {"question": "Choose the correct sentence:", "options": ["I used to smoke, but now I don't.", "I used to smoking, but now I don't.", "I use to smoke, but now I don't.", "I used to smoked, but now I don't."], "answer": 0, "skill": "grammar"},
        {"question": "Complete: 'You ___ to wear a helmet when riding a bike.'", "options": ["must", "should", "have", "need"], "answer": 1, "skill": "grammar"},
        # --- Лексика ---
        {"question": "Choose the correct word: 'The ___ of the meeting is to discuss the budget.'", "options": ["purpose", "reason", "cause", "aim"], "answer": 0, "skill": "vocabulary"},
        {"question": "What does 'environment' mean?", "options": ["the natural world", "a type of food", "a kind of music", "a building"], "answer": 0, "skill": "vocabulary"},
        {"question": "Choose the correct word: 'She has a ___ for languages.'", "options": ["talent", "skill", "ability", "gift"], "answer": 0, "skill": "vocabulary"},
        {"question": "What is the opposite of 'increase'?", "options": ["decrease", "grow", "rise", "expand"], "answer": 0, "skill": "vocabulary"},
        {"question": "Choose the correct word: 'I need to ___ my English before the exam.'", "options": ["improve", "increase", "grow", "raise"], "answer": 0, "skill": "vocabulary"},
        {"question": "What does 'opportunity' mean?", "options": ["a chance to do something", "a problem", "a mistake", "a job"], "answer": 0, "skill": "vocabulary"},
        {"question": "Choose the correct word: 'The company ___ 100 new employees last year.'", "options": ["hired", "fired", "bought", "sold"], "answer": 0, "skill": "vocabulary"},
        {"question": "What is the opposite of 'success'?", "options": ["failure", "victory", "achievement", "progress"], "answer": 0, "skill": "vocabulary"},
        {"question": "Choose the correct word: 'I'm ___ in learning new languages.'", "options": ["interested", "interesting", "interest", "interests"], "answer": 0, "skill": "vocabulary"},
        {"question": "What does 'available' mean?", "options": ["able to be used", "not able to be used", "expensive", "cheap"], "answer": 0, "skill": "vocabulary"},
    ],
    "B2": [
        # --- Грамматика ---
        {"question": "Choose the correct form: 'I wish I ___ more time.'", "options": ["have", "had", "would have", "will have"], "answer": 1, "skill": "grammar"},
        {"question": "Complete: 'The report ___ by the end of the week.'", "options": ["will be completed", "will complete", "will have completed", "completes"], "answer": 0, "skill": "grammar"},
        {"question": "Choose the correct sentence:", "options": ["She is used to work late.", "She is used to working late.", "She used to working late.", "She uses to work late."], "answer": 1, "skill": "grammar"},
        {"question": "Complete: 'Had I known, I ___ differently.'", "options": ["would act", "would have acted", "will act", "acted"], "answer": 1, "skill": "grammar"},
        {"question": "Choose the correct sentence:", "options": ["Not only he passed the exam, but also got a scholarship.", "Not only did he pass the exam, but he also got a scholarship.", "Not only he did pass the exam, but also got a scholarship.", "Not only passed he the exam, but also got a scholarship."], "answer": 1, "skill": "grammar"},
        {"question": "Complete: 'The project ___ by the time we arrived.'", "options": ["was finished", "had been finished", "has been finished", "is finished"], "answer": 1, "skill": "grammar"},
        {"question": "Choose the correct form: 'I'd rather you ___ smoke in here.'", "options": ["don't", "didn't", "won't", "wouldn't"], "answer": 1, "skill": "grammar"},
        {"question": "Complete: 'She insisted that he ___ the report immediately.'", "options": ["submits", "submit", "submitted", "is submitting"], "answer": 1, "skill": "grammar"},
        {"question": "Choose the correct sentence:", "options": ["Despite of the rain, we went out.", "Despite the rain, we went out.", "Despite the rain, we went out.", "Despite the rain, we went out."], "answer": 1, "skill": "grammar"},
        {"question": "Complete: 'By next year, I ___ here for 10 years.'", "options": ["will work", "will have worked", "have worked", "work"], "answer": 1, "skill": "grammar"},
        # --- Лексика ---
        {"question": "Choose the correct word: 'The ___ of the new policy was immediate.'", "options": ["impact", "effect", "influence", "result"], "answer": 0, "skill": "vocabulary"},
        {"question": "What does 'controversial' mean?", "options": ["causing disagreement", "very interesting", "very old", "very easy"], "answer": 0, "skill": "vocabulary"},
        {"question": "Choose the correct word: 'She ___ her success to hard work.'", "options": ["attributes", "contributes", "distributes", "tributes"], "answer": 0, "skill": "vocabulary"},
        {"question": "What is the opposite of 'significant'?", "options": ["insignificant", "important", "major", "crucial"], "answer": 0, "skill": "vocabulary"},
        {"question": "Choose the correct word: 'The ___ of the population lives in cities.'", "options": ["majority", "minority", "major", "majorly"], "answer": 0, "skill": "vocabulary"},
        {"question": "What does 'ambiguous' mean?", "options": ["having more than one meaning", "very clear", "very simple", "very long"], "answer": 0, "skill": "vocabulary"},
        {"question": "Choose the correct word: 'We need to ___ the risks before proceeding.'", "options": ["assess", "access", "excess", "process"], "answer": 0, "skill": "vocabulary"},
        {"question": "What is the opposite of 'temporary'?", "options": ["permanent", "brief", "short", "momentary"], "answer": 0, "skill": "vocabulary"},
        {"question": "Choose the correct word: 'The ___ of the argument was convincing.'", "options": ["validity", "valid", "value", "volume"], "answer": 0, "skill": "vocabulary"},
        {"question": "What does 'inevitable' mean?", "options": ["unavoidable", "impossible", "unlikely", "unnecessary"], "answer": 0, "skill": "vocabulary"},
    ],
    "C1": [
        # --- Грамматика ---
        {"question": "Choose the correct sentence:", "options": ["Despite of the rain, we went out.", "Despite the rain, we went out.", "Despite the rain, we went out.", "Despite the rain, we went out."], "answer": 1, "skill": "grammar"},
        {"question": "Complete: 'Had I known about the meeting, I ___ attended.'", "options": ["would have", "will have", "would", "have"], "answer": 0, "skill": "grammar"},
        {"question": "Choose the correct form: 'The manager insisted that the report ___ immediately.'", "options": ["is submitted", "be submitted", "was submitted", "submitted"], "answer": 1, "skill": "grammar"},
        {"question": "Complete: 'It's high time we ___ a decision.'", "options": ["make", "made", "will make", "would make"], "answer": 1, "skill": "grammar"},
        {"question": "Choose the correct sentence:", "options": ["I wish I would have studied harder.", "I wish I had studied harder.", "I wish I studied harder.", "I wish I would study harder."], "answer": 1, "skill": "grammar"},
        {"question": "Complete: 'The proposal ___ by the committee before it was approved.'", "options": ["was reviewed", "had been reviewed", "has been reviewed", "is reviewed"], "answer": 1, "skill": "grammar"},
        {"question": "Choose the correct form: 'Were it not for your help, we ___ the project.'", "options": ["wouldn't finish", "wouldn't have finished", "didn't finish", "haven't finished"], "answer": 1, "skill": "grammar"},
        {"question": "Complete: 'She ___ to have finished the report by now.'", "options": ["is supposed", "supposed", "supposes", "is supposing"], "answer": 0, "skill": "grammar"},
        {"question": "Choose the correct sentence:", "options": ["The data suggests a clear trend.", "The data suggest a clear trend.", "The data suggesting a clear trend.", "The data are suggesting a clear trend."], "answer": 0, "skill": "grammar"},
        {"question": "Complete: '___ the weather, we decided to cancel the trip.'", "options": ["Given", "Giving", "Gave", "Given that"], "answer": 0, "skill": "grammar"},
        # --- Лексика ---
        {"question": "Choose the correct word: 'The ___ of the situation was clear to everyone.'", "options": ["gravity", "gravy", "gratitude", "grandeur"], "answer": 0, "skill": "vocabulary"},
        {"question": "What does 'meticulous' mean?", "options": ["very careful and precise", "very careless", "very fast", "very slow"], "answer": 0, "skill": "vocabulary"},
        {"question": "Choose the correct word: 'Her ___ to the problem was innovative.'", "options": ["approach", "approval", "appraisal", "apprehension"], "answer": 0, "skill": "vocabulary"},
        {"question": "What is the opposite of 'profound'?", "options": ["superficial", "deep", "serious", "significant"], "answer": 0, "skill": "vocabulary"},
        {"question": "Choose the correct word: 'The ___ of the evidence was overwhelming.'", "options": ["weight", "wait", "wet", "wheat"], "answer": 0, "skill": "vocabulary"},
        {"question": "What does 'ubiquitous' mean?", "options": ["present everywhere", "rare", "hidden", "temporary"], "answer": 0, "skill": "vocabulary"},
        {"question": "Choose the correct word: 'He ___ the importance of the issue.'", "options": ["emphasized", "emphasized on", "emphasized about", "emphasized for"], "answer": 0, "skill": "vocabulary"},
        {"question": "What is the opposite of 'coherent'?", "options": ["incoherent", "clear", "logical", "consistent"], "answer": 0, "skill": "vocabulary"},
        {"question": "Choose the correct word: 'The ___ of the argument was based on false premises.'", "options": ["validity", "valid", "value", "volume"], "answer": 0, "skill": "vocabulary"},
        {"question": "What does 'pragmatic' mean?", "options": ["practical and realistic", "theoretical", "idealistic", "emotional"], "answer": 0, "skill": "vocabulary"},
    ],
    "C2": [
        # --- Грамматика ---
        {"question": "Choose the correct sentence:", "options": ["The data suggests a clear trend.", "The data suggest a clear trend.", "The data suggesting a clear trend.", "The data are suggesting a clear trend."], "answer": 0, "skill": "grammar"},
        {"question": "Complete: 'Not only ___ the exam, but she also got the highest score.'", "options": ["she passed", "did she pass", "she did pass", "passed she"], "answer": 1, "skill": "grammar"},
        {"question": "Choose the correct form: 'Were it not for your help, we ___ the project.'", "options": ["wouldn't finish", "wouldn't have finished", "didn't finish", "haven't finished"], "answer": 1, "skill": "grammar"},
        {"question": "Complete: 'Scarcely ___ the door when the phone rang.'", "options": ["had he closed", "he had closed", "he closed", "did he close"], "answer": 0, "skill": "grammar"},
        {"question": "Choose the correct sentence:", "options": ["The committee are divided on the issue.", "The committee is divided on the issue.", "The committee were divided on the issue.", "The committee have divided on the issue."], "answer": 1, "skill": "grammar"},
        {"question": "Complete: 'It is imperative that she ___ the deadline.'", "options": ["meets", "meet", "met", "is meeting"], "answer": 1, "skill": "grammar"},
        {"question": "Choose the correct form: 'The findings, ___ were unexpected, changed our understanding.'", "options": ["which", "that", "what", "who"], "answer": 0, "skill": "grammar"},
        {"question": "Complete: '___ the complexity of the issue, a thorough analysis is required.'", "options": ["Given", "Giving", "Gave", "Given that"], "answer": 0, "skill": "grammar"},
        {"question": "Choose the correct sentence:", "options": ["I would rather you didn't mention it.", "I would rather you don't mention it.", "I would rather you won't mention it.", "I would rather you wouldn't mention it."], "answer": 0, "skill": "grammar"},
        {"question": "Complete: 'The proposal, ___ was submitted last week, has been approved.'", "options": ["which", "that", "what", "who"], "answer": 0, "skill": "grammar"},
        # --- Лексика ---
        {"question": "Choose the correct word: 'The ___ of the argument was both logical and persuasive.'", "options": ["cogency", "cognition", "cognizance", "cognate"], "answer": 0, "skill": "vocabulary"},
        {"question": "What does 'ephemeral' mean?", "options": ["lasting a very short time", "lasting forever", "very large", "very small"], "answer": 0, "skill": "vocabulary"},
        {"question": "Choose the correct word: 'Her ___ remarks during the debate were widely criticized.'", "options": ["vitriolic", "vitamin", "vital", "virtual"], "answer": 0, "skill": "vocabulary"},
        {"question": "What is the opposite of 'obfuscate'?", "options": ["clarify", "confuse", "complicate", "obscure"], "answer": 0, "skill": "vocabulary"},
        {"question": "Choose the correct word: 'The ___ of the situation required immediate action.'", "options": ["gravity", "gravy", "gratitude", "grandeur"], "answer": 0, "skill": "vocabulary"},
        {"question": "What does 'sycophantic' mean?", "options": ["excessively flattering", "very honest", "very critical", "very independent"], "answer": 0, "skill": "vocabulary"},
        {"question": "Choose the correct word: 'The ___ of the evidence was undeniable.'", "options": ["weight", "wait", "wet", "wheat"], "answer": 0, "skill": "vocabulary"},
        {"question": "What is the opposite of 'prolific'?", "options": ["unproductive", "productive", "creative", "fertile"], "answer": 0, "skill": "vocabulary"},
        {"question": "Choose the correct word: 'His ___ approach to the problem was refreshing.'", "options": ["unorthodox", "orthodox", "traditional", "conventional"], "answer": 0, "skill": "vocabulary"},
        {"question": "What does 'quintessential' mean?", "options": ["the most perfect example", "the worst example", "a rare example", "an unusual example"], "answer": 0, "skill": "vocabulary"},
    ],
}


def get_questions_for_level(level, skill=None, exclude=None):
    """Возвращает вопросы для уровня, опционально фильтруя по навыку."""
    questions = QUESTION_BANK.get(level, [])
    if skill:
        questions = [q for q in questions if q.get("skill") == skill]
    if exclude:
        excluded = {q["question"] for q in exclude}
        questions = [q for q in questions if q["question"] not in excluded]
    return questions


def get_all_questions():
    """Возвращает все вопросы из банка."""
    all_q = []
    for level in ["A1", "A2", "B1", "B2", "C1", "C2"]:
        all_q.extend(QUESTION_BANK.get(level, []))
    return all_q
