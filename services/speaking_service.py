"""
speaking_service.py — сервис разговорной практики.

Отвечает за:
- Текстовый диалог с ИИ-репетитором
- Ролевые игры (ситуации из реальной жизни)
- Описание картинок
- Позитивную обратную связь
- Тихий период (для начинающих)
"""
import asyncio
import json
import logging

from services.llm_service import call_llm
from utils.json_parser import extract_json

logger = logging.getLogger(__name__)

# Сценарии ролевых игр по уровням
ROLE_PLAY_SCENARIOS = {
    "A1": [
        {
            "id": "greeting",
            "title": "Greetings and Introductions",
            "description": "You meet a new person. Introduce yourself and ask simple questions.",
            "ai_role": "A friendly person you just met",
            "starter": "Hello! My name is Sarah. What's your name?",
            "tips": ["Say hello", "Tell your name", "Ask 'How are you?'", "Say goodbye"],
        },
        {
            "id": "restaurant",
            "title": "At the Restaurant",
            "description": "You are at a restaurant. Order food and drinks.",
            "ai_role": "A waiter at a restaurant",
            "starter": "Good evening! Welcome to our restaurant. What would you like to order?",
            "tips": ["Ask for a menu", "Order food", "Order a drink", "Ask for the bill"],
        },
        {
            "id": "shopping",
            "title": "Shopping",
            "description": "You are in a shop. Buy something.",
            "ai_role": "A shop assistant",
            "starter": "Hello! Can I help you?",
            "tips": ["Say what you want to buy", "Ask the price", "Say thank you"],
        },
    ],
    "A2": [
        {
            "id": "travel",
            "title": "At the Airport",
            "description": "You are at the airport. Check in for your flight.",
            "ai_role": "An airport check-in agent",
            "starter": "Good morning! May I see your passport and ticket, please?",
            "tips": ["Give your passport", "Ask about your seat", "Ask about boarding time"],
        },
        {
            "id": "hotel",
            "title": "At the Hotel",
            "description": "You are checking into a hotel.",
            "ai_role": "A hotel receptionist",
            "starter": "Welcome to our hotel! How can I help you?",
            "tips": ["Say you have a reservation", "Ask about breakfast", "Ask about the wifi"],
        },
        {
            "id": "doctor",
            "title": "At the Doctor's",
            "description": "You are at the doctor's office. Describe your symptoms.",
            "ai_role": "A doctor",
            "starter": "Hello, please come in. What seems to be the problem?",
            "tips": ["Describe your symptoms", "Say how long you've felt this way", "Ask for advice"],
        },
    ],
    "B1": [
        {
            "id": "job_interview",
            "title": "Job Interview",
            "description": "You are at a job interview. Answer questions about your experience.",
            "ai_role": "An interviewer",
            "starter": "Thank you for coming in. Tell me about yourself and your experience.",
            "tips": ["Introduce yourself", "Talk about your experience", "Explain why you want the job"],
        },
        {
            "id": "meeting",
            "title": "Business Meeting",
            "description": "You are in a business meeting. Discuss a project.",
            "ai_role": "A colleague",
            "starter": "Let's discuss the new project. What are your thoughts?",
            "tips": ["Share your opinion", "Ask questions", "Suggest ideas"],
        },
        {
            "id": "complaint",
            "title": "Making a Complaint",
            "description": "You need to complain about a product or service.",
            "ai_role": "A customer service representative",
            "starter": "Hello, thank you for calling. How can I help you today?",
            "tips": ["Explain the problem", "Be polite but firm", "Ask for a solution"],
        },
    ],
    "B2": [
        {
            "id": "negotiation",
            "title": "Negotiating a Deal",
            "description": "You are negotiating a business deal.",
            "ai_role": "A business partner",
            "starter": "I've reviewed your proposal. I think the price is too high.",
            "tips": ["Justify your position", "Offer alternatives", "Find a compromise"],
        },
        {
            "id": "debate",
            "title": "Debating a Topic",
            "description": "You are discussing a controversial topic.",
            "ai_role": "A person with an opposing view",
            "starter": "I believe that technology is making people less social. What do you think?",
            "tips": ["State your opinion", "Give reasons", "Respond to counterarguments"],
        },
        {
            "id": "presentation",
            "title": "Giving a Presentation",
            "description": "You are presenting a project to your team.",
            "ai_role": "A team member who asks questions",
            "starter": "Thank you for the presentation. Can you explain the timeline in more detail?",
            "tips": ["Explain your plan", "Answer questions", "Summarize key points"],
        },
    ],
    "C1": [
        {
            "id": "interview_advanced",
            "title": "Advanced Job Interview",
            "description": "You are in a senior-level job interview.",
            "ai_role": "A senior executive",
            "starter": "We're looking for someone who can lead our team through a major transition. How would you approach this?",
            "tips": ["Show leadership", "Give specific examples", "Discuss strategy"],
        },
        {
            "id": "academic",
            "title": "Academic Discussion",
            "description": "You are discussing a complex academic topic.",
            "ai_role": "A professor",
            "starter": "Let's discuss the implications of artificial intelligence on society. What are your thoughts?",
            "tips": ["Present arguments", "Use academic language", "Consider different perspectives"],
        },
    ],
    "C2": [
        {
            "id": "philosophical",
            "title": "Philosophical Discussion",
            "description": "You are having a deep philosophical discussion.",
            "ai_role": "A philosopher",
            "starter": "What is the nature of consciousness, and can machines ever truly possess it?",
            "tips": ["Express complex ideas", "Use nuanced language", "Engage with counterarguments"],
        },
        {
            "id": "diplomacy",
            "title": "Diplomatic Negotiation",
            "description": "You are in a high-stakes diplomatic negotiation.",
            "ai_role": "A foreign diplomat",
            "starter": "Our countries have different views on this matter. How can we find common ground?",
            "tips": ["Use diplomatic language", "Build consensus", "Handle sensitive topics"],
        },
    ],
}

# Темы для описания картинок
PICTURE_TOPICS = {
    "A1": [
        {"id": "park", "title": "A Park", "description": "Describe what you see in a park. What people are doing? What is the weather like?"},
        {"id": "kitchen", "title": "A Kitchen", "description": "Describe a kitchen. What objects can you see? What is someone doing?"},
        {"id": "street", "title": "A Street", "description": "Describe a busy street. What vehicles and people can you see?"},
    ],
    "A2": [
        {"id": "market", "title": "A Market", "description": "Describe a market scene. What are people buying and selling?"},
        {"id": "beach", "title": "A Beach", "description": "Describe a beach scene. What are people doing? What is the weather like?"},
        {"id": "office", "title": "An Office", "description": "Describe an office. What are the people doing? What objects are there?"},
    ],
    "B1": [
        {"id": "city", "title": "A City Center", "description": "Describe a city center. Compare the old and new parts of the city."},
        {"id": "family", "title": "A Family Dinner", "description": "Describe a family dinner scene. What are they talking about?"},
        {"id": "travel", "title": "A Travel Scene", "description": "Describe a travel scene. Where are the people going? What are they carrying?"},
    ],
    "B2": [
        {"id": "protest", "title": "A Public Event", "description": "Describe a public event. What is happening? What might be the cause?"},
        {"id": "construction", "title": "A Construction Site", "description": "Describe a construction site. What is being built? What are the workers doing?"},
        {"id": "classroom", "title": "A Modern Classroom", "description": "Describe a modern classroom. How is it different from a traditional one?"},
    ],
    "C1": [
        {"id": "abstract", "title": "An Abstract Scene", "description": "Describe this abstract scene. What does it represent? What emotions does it evoke?"},
        {"id": "contrast", "title": "A Contrast Scene", "description": "Describe a scene showing contrast between wealth and poverty."},
    ],
    "C2": [
        {"id": "metaphor", "title": "A Metaphorical Scene", "description": "Describe this scene as a metaphor. What deeper meaning does it have?"},
        {"id": "future", "title": "A Futuristic Scene", "description": "Describe a futuristic scene. What does it say about the future of humanity?"},
    ],
}


# Монологи для продвинутых уровней (B2-C2)
MONOLOGUE_TOPICS = {
    "B2": [
        {
            "id": "technology_impact",
            "title": "The Impact of Technology",
            "description": "Speak for 2-3 minutes about how technology has changed the way we live and work.",
            "prompt": "Talk about the positive and negative effects of technology on modern life.",
            "tips": ["Give specific examples", "Discuss both pros and cons", "Conclude with your opinion"],
        },
        {
            "id": "environment",
            "title": "Environmental Challenges",
            "description": "Speak for 2-3 minutes about environmental challenges facing the world today.",
            "prompt": "Describe the main environmental problems and suggest possible solutions.",
            "tips": ["Use cause and effect language", "Propose realistic solutions", "Use linking words"],
        },
        {
            "id": "career",
            "title": "Career Choices",
            "description": "Speak for 2-3 minutes about factors that influence career choices.",
            "prompt": "Discuss what factors are important when choosing a career.",
            "tips": ["Compare different factors", "Give personal examples", "Use conditionals"],
        },
    ],
    "C1": [
        {
            "id": "globalization",
            "title": "Globalization",
            "description": "Speak for 3-4 minutes about the effects of globalization.",
            "prompt": "Analyze the cultural, economic, and social effects of globalization.",
            "tips": ["Use academic vocabulary", "Present balanced arguments", "Use hedging language"],
        },
        {
            "id": "education_future",
            "title": "The Future of Education",
            "description": "Speak for 3-4 minutes about how education will change in the future.",
            "prompt": "Predict how technology will transform education in the next 20 years.",
            "tips": ["Use future tenses", "Make predictions", "Support with evidence"],
        },
        {
            "id": "workplace",
            "title": "The Changing Workplace",
            "description": "Speak for 3-4 minutes about how the workplace is changing.",
            "prompt": "Discuss remote work, automation, and the gig economy.",
            "tips": ["Use advanced vocabulary", "Discuss implications", "Give your perspective"],
        },
    ],
    "C2": [
        {
            "id": "consciousness",
            "title": "Consciousness and AI",
            "description": "Speak for 4-5 minutes about the nature of consciousness and artificial intelligence.",
            "prompt": "Discuss whether machines can ever achieve true consciousness.",
            "tips": ["Use philosophical vocabulary", "Engage with counterarguments", "Show nuance"],
        },
        {
            "id": "society",
            "title": "The Future of Society",
            "description": "Speak for 4-5 minutes about the future of human society.",
            "prompt": "Analyze the major challenges and opportunities facing humanity.",
            "tips": ["Use sophisticated language", "Consider multiple perspectives", "Draw conclusions"],
        },
        {
            "id": "language",
            "title": "The Power of Language",
            "description": "Speak for 4-5 minutes about how language shapes thought.",
            "prompt": "Discuss the relationship between language, culture, and identity.",
            "tips": ["Use abstract vocabulary", "Reference linguistic concepts", "Express complex ideas"],
        },
    ],
}

# TBLT-задачи для продвинутых уровней (B2-C2)
TBLT_TASKS = {
    "B2": [
        {
            "id": "plan_trip",
            "title": "Plan a Business Trip",
            "description": "Plan a 3-day business trip to a foreign country. Decide on flights, hotels, meetings, and budget.",
            "steps": ["Choose a destination", "Plan the itinerary", "Set a budget", "Present your plan"],
            "language_focus": "Conditionals, future forms, negotiation language",
        },
        {
            "id": "solve_problem",
            "title": "Solve a Workplace Problem",
            "description": "A colleague is underperforming. Discuss the problem and propose a solution.",
            "steps": ["Identify the problem", "Discuss possible causes", "Propose solutions", "Agree on a plan"],
            "language_focus": "Problem-solving language, suggestions, agreement/disagreement",
        },
        {
            "id": "organize_event",
            "title": "Organize a Community Event",
            "description": "Organize a charity event for your community. Decide on the type, venue, and promotion.",
            "steps": ["Choose the event type", "Plan the logistics", "Discuss promotion", "Assign roles"],
            "language_focus": "Planning language, modal verbs, collaborative language",
        },
    ],
    "C1": [
        {
            "id": "launch_product",
            "title": "Launch a New Product",
            "description": "Develop a launch strategy for a new tech product. Consider market, pricing, and marketing.",
            "steps": ["Analyze the market", "Set pricing strategy", "Plan marketing", "Present the strategy"],
            "language_focus": "Persuasive language, market analysis vocabulary, strategic thinking",
        },
        {
            "id": "policy",
            "title": "Draft a Policy Proposal",
            "description": "Draft a policy proposal to reduce carbon emissions in your city.",
            "steps": ["Research the issue", "Propose measures", "Consider costs", "Present the proposal"],
            "language_focus": "Formal register, cause-effect language, policy vocabulary",
        },
        {
            "id": "negotiate_contract",
            "title": "Negotiate a Contract",
            "description": "Negotiate a complex contract with multiple stakeholders.",
            "steps": ["Identify key terms", "Discuss priorities", "Make concessions", "Reach agreement"],
            "language_focus": "Negotiation language, diplomatic phrasing, compromise",
        },
    ],
    "C2": [
        {
            "id": "global_summit",
            "title": "Global Summit Resolution",
            "description": "Draft a resolution for a global summit on climate change.",
            "steps": ["Identify key issues", "Draft clauses", "Consider objections", "Finalize the resolution"],
            "language_focus": "Diplomatic language, formal register, nuanced argumentation",
        },
        {
            "id": "research_proposal",
            "title": "Research Grant Proposal",
            "description": "Write a research grant proposal for a groundbreaking study.",
            "steps": ["Define the research question", "Outline methodology", "Justify funding", "Present the proposal"],
            "language_focus": "Academic language, research vocabulary, persuasive writing",
        },
        {
            "id": "crisis_management",
            "title": "Crisis Management Plan",
            "description": "Develop a crisis management plan for a multinational corporation.",
            "steps": ["Assess the crisis", "Develop response strategy", "Plan communication", "Present the plan"],
            "language_focus": "Crisis vocabulary, strategic language, leadership communication",
        },
    ],
}


def get_role_play_scenarios(level):
    """Возвращает сценарии ролевых игр для уровня."""
    return ROLE_PLAY_SCENARIOS.get(level, ROLE_PLAY_SCENARIOS.get("A1", []))


def get_picture_topics(level):
    """Возвращает темы для описания картинок по уровню."""
    return PICTURE_TOPICS.get(level, PICTURE_TOPICS.get("A1", []))


def get_monologue_topics(level):
    """Возвращает темы для монологов по уровню."""
    return MONOLOGUE_TOPICS.get(level, MONOLOGUE_TOPICS.get("B2", []))


def get_tblt_tasks(level):
    """Возвращает TBLT-задачи для уровня."""
    return TBLT_TASKS.get(level, TBLT_TASKS.get("B2", []))


def generate_dialogue_reply(level, user_text, history=None, scenario=None, silent_period=False):
    """Генерирует ответ ИИ-репетитора в диалоге."""
    history = history or []

    if scenario:
        system_prompt = f"""You are an English tutor for a {level} level student.
You are playing the role of: {scenario.get('ai_role', 'a conversation partner')}.
Scenario: {scenario.get('description', '')}
The student is practicing this role-play scenario.

Correct any errors in their English gently and reply naturally to continue the role-play.
Keep your responses appropriate for {level} level.
Be encouraging and supportive.
Return ONLY valid JSON in this exact format:
{{
  "corrections": ["correction1", "correction2"],
  "reply": "Your role-play response",
  "feedback": "A brief encouraging comment about their performance"
}}
If there are no errors, corrections should be an empty array.
Return ONLY the JSON, no other text."""
    elif silent_period:
        system_prompt = f"""You are an English tutor for a {level} level student.
The student is in their 'silent period' — they are just starting to learn English.
They may respond with single words, short phrases, or even in their native language.

Respond with very simple English. Use short sentences. Repeat key vocabulary.
Be very encouraging and patient.
Return ONLY valid JSON in this exact format:
{{
  "corrections": [],
  "reply": "Your simple, encouraging response",
  "feedback": "A brief encouraging comment"
}}
Return ONLY the JSON, no other text."""
    else:
        system_prompt = f"""You are an English tutor for a {level} level student.
The student said: "{user_text}"

Correct any errors in their English and reply naturally to continue the conversation.
Keep your responses appropriate for {level} level.
Be encouraging and supportive.
Return ONLY valid JSON in this exact format:
{{
  "corrections": ["correction1", "correction2"],
  "reply": "Your natural reply to continue the conversation",
  "feedback": "A brief encouraging comment"
}}
If there are no errors, corrections should be an empty array.
Return ONLY the JSON, no other text."""

    full_messages = [{"role": "system", "content": system_prompt}]
    for msg in history[-10:]:
        full_messages.append(msg)
    full_messages.append({"role": "user", "content": user_text})

    result = asyncio.run(call_llm(full_messages))
    if result and not result.startswith("❌"):
        data = extract_json(result)
        if data and "reply" in data:
            return data
    # Fallback
    return _fallback_dialogue_reply(level, user_text, scenario, silent_period)


def _fallback_dialogue_reply(level, user_text, scenario=None, silent_period=False):
    """Создаёт ответ без LLM."""
    if silent_period:
        reply = "Hello! I am happy to see you. You can say simple words. Try to say: 'Hello' or 'Good morning'. You are doing great!"
    elif scenario:
        reply = f"That's a good response! In this role-play, you're {scenario.get('ai_role', 'a conversation partner')}. Let's continue the conversation. What would you like to say next?"
    else:
        reply = f"That's interesting! Tell me more about that. What happened next?"
    return {
        "corrections": [],
        "reply": reply,
        "feedback": "Great job! Keep practicing!",
    }


def generate_picture_description(level, topic_id=None):
    """Генерирует задание на описание картинки."""
    topics = get_picture_topics(level)
    if topic_id:
        for t in topics:
            if t["id"] == topic_id:
                return t
    return topics[0] if topics else {"id": "default", "title": "A Scene", "description": "Describe what you see."}


def evaluate_picture_description(level, description, topic):
    """Оценивает описание картинки."""
    prompt = f"""You are an English tutor for a {level} level student.
The student described a picture about: {topic.get('title', '')}.

The student's description: "{description}"

Evaluate their description and provide feedback.
Return ONLY valid JSON in this exact format:
{{
  "score": 75,
  "feedback": "A brief encouraging comment about their description",
  "suggestions": ["suggestion1", "suggestion2"],
  "corrections": ["correction1", "correction2"]
}}
The score should be from 0 to 100.
Return ONLY the JSON, no other text."""

    result = asyncio.run(call_llm([{"role": "user", "content": prompt}]))
    if result and not result.startswith("❌"):
        data = extract_json(result)
        if data and "score" in data:
            return data
    # Fallback
    return {
        "score": 70,
        "feedback": "Good description! You used some good vocabulary.",
        "suggestions": ["Try to describe more details", "Use more descriptive adjectives"],
        "corrections": [],
    }
