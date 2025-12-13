#!/usr/bin/env python3
"""
Create Jake - The Income Stacking Qualifier Agent
Based on the call flow and bot.py analysis
"""
import asyncio
import sys
import os
import uuid
sys.path.insert(0, '/app/backend')

from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone

async def create_agent():
    print("=" * 80)
    print("CREATING JAKE - INCOME STACKING QUALIFIER AGENT")
    print("=" * 80)
    
    # Connect to MongoDB
    MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    DB_NAME = os.environ.get("DB_NAME", "test_database")
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    agent_id = str(uuid.uuid4())
    
    # Define all nodes with proper structure
    call_flow = [
        # START NODE
        {
            "id": "1",
            "type": "start",
            "label": "Begin",
            "data": {
                "whoSpeaksFirst": "agent",
                "aiSpeaksAfterSilence": True,
                "silenceTimeout": 2000
            }
        },
        
        # N001A - Name Confirmation
        {
            "id": "2",
            "type": "conversation",
            "label": "Name Confirmation",
            "data": {
                "mode": "script",
                "content": "{{customer_name}}?",
                "transitions": [
                    {
                        "id": "t1",
                        "condition": "If user confirms name (Yes, Speaking, This is he/she, etc)",
                        "nextNode": "3"
                    },
                    {
                        "id": "t2",
                        "condition": "If wrong number (No John here, Wrong number, etc)",
                        "nextNode": "100"
                    }
                ]
            }
        },
        
        # Wrong Number Node
        {
            "id": "100",
            "type": "ending",
            "label": "Wrong Number",
            "data": {
                "mode": "script",
                "content": "My apologies, it seems I have the wrong number. Have a good day.",
                "transitions": []
            }
        },
        
        # N001B - Intro and Help Request
        {
            "id": "3",
            "type": "conversation",
            "label": "Intro & Help Request",
            "data": {
                "mode": "script",
                "content": "This is Jake. I was just, um, wondering if you could possibly help me out for a moment?",
                "transitions": [
                    {
                        "id": "t3",
                        "condition": "User responds (any verbal response)",
                        "nextNode": "4"
                    }
                ]
            }
        },
        
        # N_Opener - Stacking Income Hook
        {
            "id": "4",
            "type": "conversation",
            "label": "Stacking Income Hook",
            "data": {
                "mode": "script",
                "content": "Well, uh... I don't know if you could yet, but, I'm calling because you filled out an ad about stacking income without stacking hours. I know this call is out of the blue, but do you have just 25 seconds for me to explain why I'm reaching out today specifically?",
                "transitions": [
                    {
                        "id": "t4",
                        "condition": "If they agree or ask for context (yes, sure, what is this about)",
                        "nextNode": "5"
                    },
                    {
                        "id": "t5",
                        "condition": "If they don't recall the ad",
                        "nextNode": "6"
                    },
                    {
                        "id": "t6",
                        "condition": "If they object or say no",
                        "nextNode": "7"
                    },
                    {
                        "id": "t7",
                        "condition": "If they say no time or ask to be called back",
                        "nextNode": "8"
                    }
                ]
            }
        },
        
        # N_IntroduceModel - Explain Business Model
        {
            "id": "5",
            "type": "conversation",
            "label": "Introduce Model",
            "data": {
                "mode": "script",
                "content": "Okay. In a nutshell, we set up passive income websites, and we let them produce income for you. What questions come to mind as soon as you hear something like that?",
                "transitions": [
                    {
                        "id": "t8",
                        "condition": "After answering initial questions",
                        "nextNode": "9"
                    }
                ]
            }
        },
        
        # N003 - No Recall Pivot
        {
            "id": "6",
            "type": "conversation",
            "label": "No Recall Pivot",
            "data": {
                "mode": "script",
                "content": "Gotcha. Are you focused on creating new income streams right now?",
                "transitions": [
                    {
                        "id": "t9",
                        "condition": "If yes or shows curiosity",
                        "nextNode": "5"
                    },
                    {
                        "id": "t10",
                        "condition": "If no or disinterested",
                        "nextNode": "101"
                    }
                ]
            }
        },
        
        # End - Not Interested
        {
            "id": "101",
            "type": "ending",
            "label": "Not Interested",
            "data": {
                "mode": "script",
                "content": "I understand. Thanks for your time. Have a great day.",
                "transitions": []
            }
        },
        
        # N003B - Deframe Initial Objection
        {
            "id": "7",
            "type": "conversation",
            "label": "Deframe Objection",
            "data": {
                "mode": "prompt",
                "content": "Handle the objection using appropriate tactics. For trust/scam concerns, acknowledge and ask about their biggest fear. For disinterest, ask if they're completely set with current income and free time. For time objections, ask if it's about finding a few minutes now or the bigger time commitment. Once they show curiosity, transition forward.",
                "transitions": [
                    {
                        "id": "t11",
                        "condition": "If they show curiosity (tell me more, how does it work, okay, yes)",
                        "nextNode": "5"
                    },
                    {
                        "id": "t12",
                        "condition": "If they ask to be called back or say they have to go",
                        "nextNode": "8"
                    }
                ]
            }
        },
        
        # N_Obj Early Dismiss - Ask Share Background
        {
            "id": "8",
            "type": "conversation",
            "label": "Early Dismiss - Share Background",
            "data": {
                "mode": "script",
                "content": "I understand the skepticism. I was skeptical too until I became a student myself. And I'm not just any student. Do you mind if I take 20 seconds to share a bit about my background?",
                "transitions": [
                    {
                        "id": "t13",
                        "condition": "If they agree (Yes, Sure, Okay, or No meaning they don't mind)",
                        "nextNode": "10"
                    },
                    {
                        "id": "t14",
                        "condition": "If they decline or object further",
                        "nextNode": "11"
                    }
                ]
            }
        },
        
        # KB Q&A with Strategic Narrative
        {
            "id": "9",
            "type": "conversation",
            "label": "Q&A Strategic Narrative",
            "data": {
                "mode": "prompt",
                "content": "Answer their questions about the business. If they ask about price, say: 'That's exactly what the call with Kendrick is designed to figure out. It wouldn't be fair to throw out a number without knowing if this is even the right fit for you, would it?' After answering questions, ask the value-framing question: 'Okay, great. So with all that in mind, would you honestly be upset if you had an extra twenty thousand dollars a month coming in?'",
                "transitions": [
                    {
                        "id": "t15",
                        "condition": "If they respond positively (No who would be, That would be great)",
                        "nextNode": "12"
                    }
                ]
            }
        },
        
        # Share Background - Story Hook
        {
            "id": "10",
            "type": "conversation",
            "label": "Share Background Hook",
            "data": {
                "mode": "script",
                "content": "Great. I'm a military veteran and I have a software engineering degree, so trust me I get how much nonsense is out there. But after actually going through this program myself, I've seen firsthand it's possible for people to pull in an extra 20,000 a month, sometimes even more. Any idea what makes that possible?",
                "transitions": [
                    {
                        "id": "t16",
                        "condition": "After any response from user",
                        "nextNode": "11"
                    }
                ]
            }
        },
        
        # Explain Reason and Explore
        {
            "id": "11",
            "type": "conversation",
            "label": "Explain & Explore",
            "data": {
                "mode": "script",
                "content": "Because thousands of students already generated over 20,000 per month and our best student John is doing over 1 million per month with it. I'm not saying you're going to get to his level... but is this range of passive income something that may be worth exploring in your opinion?",
                "transitions": [
                    {
                        "id": "t17",
                        "condition": "If they respond positively or with curiosity",
                        "nextNode": "5"
                    }
                ]
            }
        },
        
        # N200 - Work and Income Background
        {
            "id": "12",
            "type": "conversation",
            "label": "Work Background",
            "data": {
                "mode": "script",
                "content": "Alright, love that! So, are you working for someone right now or do you run your own business?",
                "transitions": [
                    {
                        "id": "t18",
                        "condition": "If they have a job (employed)",
                        "nextNode": "13"
                    },
                    {
                        "id": "t19",
                        "condition": "If they are unemployed",
                        "nextNode": "14"
                    },
                    {
                        "id": "t20",
                        "condition": "If they own a business",
                        "nextNode": "15"
                    }
                ]
            }
        },
        
        # N201A - Employed Ask Yearly Income
        {
            "id": "13",
            "type": "conversation",
            "label": "Ask Yearly Income (Employed)",
            "data": {
                "mode": "script",
                "content": "Got it. And what's that job producing for you yearly, approximately?",
                "transitions": [
                    {
                        "id": "t21",
                        "condition": "After they provide income",
                        "nextNode": "16"
                    }
                ],
                "extract_variables": [
                    {
                        "name": "yearly_income",
                        "description": "The user's approximate yearly income from their job"
                    }
                ]
            }
        },
        
        # N201E - Unemployed Empathy Ask Past Income
        {
            "id": "14",
            "type": "conversation",
            "label": "Ask Past Income (Unemployed)",
            "data": {
                "mode": "script",
                "content": "Okay, I'm genuinely sorry to hear that. When you were working, what was that job producing for you yearly, roughly?",
                "transitions": [
                    {
                        "id": "t22",
                        "condition": "After they provide past income",
                        "nextNode": "17"
                    }
                ],
                "extract_variables": [
                    {
                        "name": "past_yearly_income",
                        "description": "The user's past yearly income when they were employed"
                    }
                ]
            }
        },
        
        # N202A - Business Owner Ask Monthly Revenue
        {
            "id": "15",
            "type": "conversation",
            "label": "Ask Monthly Revenue (Business)",
            "data": {
                "mode": "script",
                "content": "Okay. As a business owner, where's your monthly revenue at right now, roughly?",
                "transitions": [
                    {
                        "id": "t23",
                        "condition": "After they answer",
                        "nextNode": "18"
                    }
                ],
                "extract_variables": [
                    {
                        "name": "monthly_revenue",
                        "description": "The business owner's current monthly revenue"
                    }
                ]
            }
        },
        
        # N201B - Employed Ask Side Hustle
        {
            "id": "16",
            "type": "conversation",
            "label": "Ask Side Hustle (Employed)",
            "data": {
                "mode": "script",
                "content": "And in the last two years, did you happen to have any kind of side hustle or anything else bringing in income?",
                "transitions": [
                    {
                        "id": "t24",
                        "condition": "If yes",
                        "nextNode": "19"
                    },
                    {
                        "id": "t25",
                        "condition": "If no",
                        "nextNode": "20"
                    }
                ]
            }
        },
        
        # N201F - Unemployed Ask Side Hustle
        {
            "id": "17",
            "type": "conversation",
            "label": "Ask Side Hustle (Unemployed)",
            "data": {
                "mode": "script",
                "content": "In the last two years, did you happen to have any kind of side hustle or anything else bringing in income?",
                "transitions": [
                    {
                        "id": "t26",
                        "condition": "If yes",
                        "nextNode": "21"
                    },
                    {
                        "id": "t27",
                        "condition": "If no",
                        "nextNode": "20"
                    }
                ]
            }
        },
        
        # N202B - Ask Highest Revenue Month
        {
            "id": "18",
            "type": "conversation",
            "label": "Ask Highest Revenue (Business)",
            "data": {
                "mode": "script",
                "content": "And in the last two years, what was the highest monthly revenue point your business hit?",
                "transitions": [
                    {
                        "id": "t28",
                        "condition": "After they answer",
                        "nextNode": "20"
                    }
                ],
                "extract_variables": [
                    {
                        "name": "highest_revenue",
                        "description": "The highest monthly revenue the business achieved"
                    }
                ]
            }
        },
        
        # N201C - Employed Ask Side Hustle Amount
        {
            "id": "19",
            "type": "conversation",
            "label": "Ask Side Hustle Amount (Employed)",
            "data": {
                "mode": "script",
                "content": "Okay, great. And what was that side hustle bringing in for you, say, on a good month?",
                "transitions": [
                    {
                        "id": "t29",
                        "condition": "After they answer",
                        "nextNode": "20"
                    }
                ],
                "extract_variables": [
                    {
                        "name": "side_hustle_income",
                        "description": "Monthly income from side hustle"
                    }
                ]
            }
        },
        
        # Financial Qualification Split Logic Node
        {
            "id": "20",
            "type": "logic_split",
            "label": "Financial Qualification Check",
            "data": {
                "conditions": [
                    {
                        "variable": "yearly_income",
                        "operator": "greater_than",
                        "value": "96000",
                        "nextNode": "22"
                    },
                    {
                        "variable": "monthly_revenue",
                        "operator": "greater_than",
                        "value": "8000",
                        "nextNode": "22"
                    }
                ],
                "default_next_node": "23"
            }
        },
        
        # N201G - Unemployed Ask Side Hustle Amount
        {
            "id": "21",
            "type": "conversation",
            "label": "Ask Side Hustle Amount (Unemployed)",
            "data": {
                "mode": "script",
                "content": "Okay, great. And what does that side hustle bring in for you monthly, roughly?",
                "transitions": [
                    {
                        "id": "t30",
                        "condition": "After they answer",
                        "nextNode": "20"
                    }
                ],
                "extract_variables": [
                    {
                        "name": "side_hustle_income",
                        "description": "Monthly income from side hustle for unemployed user"
                    }
                ]
            }
        },
        
        # N_AskCapital - 15k (High Income Track)
        {
            "id": "22",
            "type": "conversation",
            "label": "Ask Capital 15-25k",
            "data": {
                "mode": "script",
                "content": "Okay, got it. For this kind of business, it definitely helps to have about fifteen to twenty-five thousand dollars in liquid capital set aside for initial expenses. Is that what you'd generally have on hand, moneywise?",
                "transitions": [
                    {
                        "id": "t31",
                        "condition": "If yes",
                        "nextNode": "25"
                    },
                    {
                        "id": "t32",
                        "condition": "If no",
                        "nextNode": "23"
                    }
                ]
            }
        },
        
        # N_AskCapital - 5k Direct
        {
            "id": "23",
            "type": "conversation",
            "label": "Ask Capital 5k",
            "data": {
                "mode": "script",
                "content": "Okay, got it. Now, for the initial expenses to get a business like this started, the absolute minimum is around five thousand dollars. Is that something you'd have access to?",
                "transitions": [
                    {
                        "id": "t33",
                        "condition": "If yes",
                        "nextNode": "25"
                    },
                    {
                        "id": "t34",
                        "condition": "If no",
                        "nextNode": "24"
                    }
                ]
            }
        },
        
        # N205C - Ask Credit Score 650
        {
            "id": "24",
            "type": "conversation",
            "label": "Ask Credit Score",
            "data": {
                "mode": "script",
                "content": "Okay, thanks for being upfront with me. The other way people qualify is with their credit. Do you have a credit score of at least six fifty?",
                "transitions": [
                    {
                        "id": "t35",
                        "condition": "If yes or they think so",
                        "nextNode": "25"
                    },
                    {
                        "id": "t36",
                        "condition": "If no",
                        "nextNode": "102"
                    }
                ]
            }
        },
        
        # Disqualified - Credit Too Low
        {
            "id": "102",
            "type": "ending",
            "label": "Disqualified",
            "data": {
                "mode": "script",
                "content": "Okay, I understand. In that case, this probably wouldn't be the right fit at this time. I appreciate you taking a few minutes to chat today. Have a great day.",
                "transitions": []
            }
        },
        
        # N401 - Ask Why Now
        {
            "id": "25",
            "type": "conversation",
            "label": "Ask Why Now",
            "data": {
                "mode": "script",
                "content": "Okay. Just to understand a bit better, is there a specific reason you're looking to make a change or explore something like this right now, as opposed to say, six months from now?",
                "transitions": [
                    {
                        "id": "t37",
                        "condition": "If they give a reason (I need more freedom, I hate my job, etc)",
                        "nextNode": "26"
                    }
                ],
                "extract_variables": [
                    {
                        "name": "motivation",
                        "description": "The user's motivation for wanting to make a change now"
                    }
                ]
            }
        },
        
        # N402 - Compliment And Ask You Know Why
        {
            "id": "26",
            "type": "conversation",
            "label": "Compliment & Hook",
            "data": {
                "mode": "script",
                "content": "Okay, I appreciate you sharing that. I have to say, that's actually refreshing to hear. You know why?",
                "transitions": [
                    {
                        "id": "t38",
                        "condition": "Whatever their response",
                        "nextNode": "27"
                    }
                ]
            }
        },
        
        # N403 - Identity Affirmation
        {
            "id": "27",
            "type": "conversation",
            "label": "Identity Affirmation",
            "data": {
                "mode": "script",
                "content": "Well, let me tell you. I sometimes talk to people that clearly will never give themselves permission to go after their dreams. But you're the type of person that is serious and ready to get started, and I commend you for that. So, does this sound like something that could fit what you're after?",
                "transitions": [
                    {
                        "id": "t39",
                        "condition": "If they respond positively (Yes, It does, I hope so)",
                        "nextNode": "28"
                    }
                ]
            }
        },
        
        # N500A - Propose Deeper Dive
        {
            "id": "28",
            "type": "conversation",
            "label": "Propose Deeper Dive",
            "data": {
                "mode": "script",
                "content": "Okay, that's excellent. I definitely feel like we can help you with that. What we need to do is set up another call that'll be a deeper dive into your situation. Sound good?",
                "transitions": [
                    {
                        "id": "t40",
                        "condition": "If they agree (Sounds good, Yes)",
                        "nextNode": "29"
                    }
                ]
            }
        },
        
        # N500B - Ask Timezone
        {
            "id": "29",
            "type": "conversation",
            "label": "Ask Timezone",
            "data": {
                "mode": "script",
                "content": "Gotcha. And just so I've got it right for our scheduling, what timezone are you in?",
                "transitions": [
                    {
                        "id": "t41",
                        "condition": "After they provide timezone",
                        "nextNode": "30"
                    }
                ],
                "extract_variables": [
                    {
                        "name": "timeZone",
                        "description": "The user's timezone"
                    }
                ]
            }
        },
        
        # N_Scheduling - Ask Time
        {
            "id": "30",
            "type": "conversation",
            "label": "Ask Schedule Time",
            "data": {
                "mode": "script",
                "content": "Okay, great! And when would be a good time for us to schedule that call?",
                "transitions": [
                    {
                        "id": "t42",
                        "condition": "After they provide a specific time",
                        "nextNode": "31"
                    }
                ],
                "extract_variables": [
                    {
                        "name": "scheduleTime",
                        "description": "The day and time they want to schedule (e.g., '3 PM tomorrow', '10 AM on Friday')"
                    }
                ]
            }
        },
        
        # N_ConfirmVideoCallEnvironment
        {
            "id": "31",
            "type": "conversation",
            "label": "Confirm Video Call Setup",
            "data": {
                "mode": "script",
                "content": "Okay, great. And just to confirm, the meeting is via Zoom, so does that time work for you to join the video call from your computer?",
                "transitions": [
                    {
                        "id": "t43",
                        "condition": "If they say yes",
                        "nextNode": "32"
                    }
                ]
            }
        },
        
        # N206 - Ask About Partners
        {
            "id": "32",
            "type": "conversation",
            "label": "Ask About Partners",
            "data": {
                "mode": "script",
                "content": "I don't think I asked, but um is there anyone else that'd be involved in your business, like a spouse or other business partners?",
                "transitions": [
                    {
                        "id": "t44",
                        "condition": "If yes",
                        "nextNode": "33"
                    },
                    {
                        "id": "t45",
                        "condition": "If no",
                        "nextNode": "34"
                    }
                ]
            }
        },
        
        # N018 - Confirm Partner Availability
        {
            "id": "33",
            "type": "conversation",
            "label": "Confirm Partner Available",
            "data": {
                "mode": "script",
                "content": "Ok cool. So can your partner 100% be on the call at that time as well?",
                "transitions": [
                    {
                        "id": "t46",
                        "condition": "If they say yes",
                        "nextNode": "34"
                    },
                    {
                        "id": "t47",
                        "condition": "If they say no or not sure",
                        "nextNode": "30"
                    }
                ]
            }
        },
        
        # N_Video - Assign Gentle Intro
        {
            "id": "34",
            "type": "conversation",
            "label": "Introduce Pre-Call Video",
            "data": {
                "mode": "script",
                "content": "Gotcha, {{customer_name}}, you're all set. Just one quick thing before your call that Kendrick likes everyone to do. There's a short 12-minute video that's just a good overview, so you've got the basics down and can really dive deep with him. Make sense?",
                "transitions": [
                    {
                        "id": "t48",
                        "condition": "After confirmation",
                        "nextNode": "35"
                    }
                ]
            }
        },
        
        # Ask if they can watch now
        {
            "id": "35",
            "type": "conversation",
            "label": "Ask Watch Now",
            "data": {
                "mode": "script",
                "content": "Great. So if I send that over when we hang up, are you able to give that a quick watch then?",
                "transitions": [
                    {
                        "id": "t49",
                        "condition": "Once they agree",
                        "nextNode": "36"
                    }
                ]
            }
        },
        
        # N_Video - Reinforce Value Fee Context
        {
            "id": "36",
            "type": "conversation",
            "label": "Reinforce Video Value",
            "data": {
                "mode": "script",
                "content": "Perfect. Yeah, it really helps make that next call super valuable. Kendrick's time is usually set at a thousand dollars for these strategy sessions, but since you'll have seen the overview, that fee is completely waived for you. All good on that front?",
                "transitions": [
                    {
                        "id": "t50",
                        "condition": "After they acknowledge",
                        "nextNode": "37"
                    }
                ]
            }
        },
        
        # N_Video - Confirm And Reply
        {
            "id": "37",
            "type": "conversation",
            "label": "Request Text Reply",
            "data": {
                "mode": "script",
                "content": "Okay, perfect. Matter of fact, I'm sending that link to your phone right now. Could you do me a favor and just reply 'Got it' so I know you received the link?",
                "transitions": [
                    {
                        "id": "t51",
                        "condition": "Once they confirm they replied (done, sent, okay I did it)",
                        "nextNode": "38"
                    }
                ]
            }
        },
        
        # N_EndCall - Final Decisive
        {
            "id": "38",
            "type": "ending",
            "label": "End Call",
            "data": {
                "mode": "script",
                "content": "Okay, perfect. You are all set then, {{customer_name}}. I've just sent that confirmation email over to you. Have a great rest of your day. Goodbye.",
                "transitions": []
            }
        }
    ]
    
    agent_data = {
        "id": agent_id,
        "name": "Jake - Income Stacking Qualifier",
        "description": "Qualification agent for passive income opportunity - handles objections, qualifies financially, and schedules strategy calls",
        "voice": "J5iaaqzR5zn6HFG4jV3b",  # Rachel voice
        "language": "English",
        "model": "gpt-4-turbo",
        "status": "active",
        "agent_type": "call_flow",
        "system_prompt": "",  # Call flow agents don't use system prompts
        "call_flow": call_flow,
        "settings": {
            "temperature": 0.7,
            "max_tokens": 500,
            "tts_speed": 1.0,
            "llm_provider": "openai",
            "tts_provider": "elevenlabs",
            "stt_provider": "deepgram",
            "deepgram_settings": {
                "endpointing": 500,
                "vad_turnoff": 250,
                "utterance_end_ms": 1000,
                "interim_results": True,
                "smart_format": True
            },
            "elevenlabs_settings": {
                "voice_id": "J5iaaqzR5zn6HFG4jV3b",
                "model": "eleven_turbo_v2_5",
                "stability": 0.5,
                "similarity_boost": 0.75,
                "style": 0.0,
                "speed": 1.0,
                "use_speaker_boost": True,
                "enable_normalization": True,
                "enable_ssml_parsing": False
            },
            "hume_settings": {
                "voice_name": "e7af7ed6-3381-48aa-ab97-49485007470b",
                "description": "warm and friendly",
                "speed": 1.0
            },
            "sesame_settings": {
                "speaker_id": 0,
                "output_format": "wav"
            },
            "melo_settings": {
                "voice": "EN-US",
                "speed": 1.2,
                "clone_wav": None
            },
            "dia_settings": {
                "voice": "S1",
                "speed": 1.0,
                "response_format": "wav"
            },
            "kokoro_settings": {
                "voice": "af_bella",
                "speed": 1.0,
                "response_format": "mp3"
            },
            "chattts_settings": {
                "voice": "female_1",
                "speed": 1.0,
                "temperature": 0.3,
                "response_format": "wav"
            },
            "assemblyai_settings": {
                "sample_rate": 8000,
                "word_boost": [],
                "enable_extra_session_information": True,
                "disable_partial_transcripts": False,
                "threshold": 0.0,
                "end_of_turn_confidence_threshold": 0.8,
                "min_end_of_turn_silence_when_confident": 500,
                "max_turn_silence": 2000
            },
            "soniox_settings": {
                "model": "stt-rt-preview-v2",
                "sample_rate": 8000,
                "audio_format": "mulaw",
                "num_channels": 1,
                "enable_endpoint_detection": True,
                "enable_speaker_diarization": False,
                "language_hints": ["en"],
                "context": ""
            }
        },
        "stats": {
            "calls_handled": 0,
            "avg_latency": 0.0,
            "success_rate": 0.0
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Insert into database
    result = await db.agents.insert_one(agent_data)
    
    print(f"\n✅ Agent created successfully!")
    print(f"   Agent ID: {agent_id}")
    print(f"   Name: {agent_data['name']}")
    print(f"   Total Nodes: {len(call_flow)}")
    print(f"\n📋 Node Breakdown:")
    print(f"   - Start: 1")
    print(f"   - Conversation: {sum(1 for n in call_flow if n['type'] == 'conversation')}")
    print(f"   - Logic Split: {sum(1 for n in call_flow if n['type'] == 'logic_split')}")
    print(f"   - Ending: {sum(1 for n in call_flow if n['type'] == 'ending')}")
    
    print(f"\n🎯 You can now edit this agent in the UI at:")
    print(f"   /agents/{agent_id}/edit")
    
    print("\n" + "=" * 80)
    
    client.close()

if __name__ == "__main__":
    asyncio.run(create_agent())
