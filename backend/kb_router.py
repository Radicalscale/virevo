"""
Smart KB Router - Determines when to use knowledge base retrieval
Fast pattern matching to avoid unnecessary RAG calls
"""
import re
import logging

logger = logging.getLogger(__name__)

# Patterns that indicate KB retrieval is NOT needed (simple conversational responses)
SIMPLE_CHAT_PATTERNS = [
    r'^(yeah|yea|yes|yep|sure|okay|ok|alright|fine)\b',
    r'^(no|nope|nah)\b',
    r'^(what|huh|hmm|uh|um)\??$',
    r'^(hello|hi|hey)\b',
    r'^(thanks|thank you|appreciate it)\b',
    r'^(bye|goodbye|see you)\b',
    r'(go ahead|continue|keep going|tell me more)',
    r'^(i\'m|i am) (good|fine|ok|busy|not interested)',
    r'(not interested|no thanks)',
]

# Patterns that definitely need KB retrieval (factual questions)
FACTUAL_QUESTION_PATTERNS = [
    r'\b(who|what|when|where|why|how)\b.*\?',  # Question words
    r'\b(tell me about|explain|describe)\b',  # Explicit requests
    r'\b(price|cost|pricing|fee|charge)\b',  # Pricing questions
    r'\b(founder|ceo|owner|company|business)\b',  # Company info
    r'\b(product|service|offer|feature)\b',  # Product questions
    r'\b(location|address|office|based)\b',  # Location questions
    r'\b(how long|how many|how much)\b',  # Quantitative questions
]

def needs_knowledge_base(user_message: str, conversation_context: list = None) -> tuple[bool, str]:
    """
    Determine if user message requires KB retrieval
    
    Args:
        user_message: The user's message
        conversation_context: Recent conversation history (optional)
    
    Returns:
        (needs_kb: bool, reason: str)
    """
    if not user_message or len(user_message.strip()) < 2:
        return (False, "empty_message")
    
    message_lower = user_message.lower().strip()
    
    # Check simple chat patterns first (most common, fastest to check)
    for pattern in SIMPLE_CHAT_PATTERNS:
        if re.search(pattern, message_lower, re.IGNORECASE):
            logger.info(f"🚦 KB Router: SKIP (simple chat pattern matched)")
            return (False, "simple_chat")
    
    # Check factual question patterns
    for pattern in FACTUAL_QUESTION_PATTERNS:
        if re.search(pattern, message_lower, re.IGNORECASE):
            logger.info(f"🚦 KB Router: USE KB (factual question pattern matched)")
            return (True, "factual_question")
    
    # Default: Check message length and complexity
    # Short messages (<10 words) are likely simple responses
    word_count = len(message_lower.split())
    if word_count < 10:
        logger.info(f"🚦 KB Router: SKIP (short message: {word_count} words)")
        return (False, "short_message")
    
    # Medium/long messages without clear patterns - use KB to be safe
    logger.info(f"🚦 KB Router: USE KB (default for medium/long message)")
    return (True, "default_long")


def get_perceptual_filler(query_type: str = "general") -> str:
    """
    Get a perceptual filler phrase to use while retrieving KB
    Masks latency and sounds natural - uses variety to avoid robotic repetition
    """
    import random
    
    fillers = {
        "general": [
            "Let me check that for you...",
            "Good question, one second...",
            "Let me pull that up real quick...",
            "Hmm, let me see...",
            "Give me just a moment...",
            "Let me grab that info...",
        ],
        "company": [
            "Let me pull up that info...",
            "Great question, let me check...",
            "One sec, let me find that...",
            "Let me get you those details...",
        ],
        "pricing": [
            "Sure, let me get those details...",
            "Good question, let me check the pricing...",
            "One moment, pulling up the costs...",
            "Let me grab those numbers for you...",
        ],
        "product": [
            "Let me look that up...",
            "Good question, let me check that...",
            "One sec, let me pull that info...",
            "Let me get you the details on that...",
        ],
        "location": [
            "Good question, let me confirm...",
            "Let me check where we're based...",
            "One moment, let me get that location info...",
        ]
    }
    
    # Randomly select from available variations
    options = fillers.get(query_type, fillers["general"])
    return random.choice(options)
