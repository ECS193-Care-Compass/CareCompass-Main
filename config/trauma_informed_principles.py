"""
SAMHSA's Six Key Principles of Trauma-Informed Care
Based on SAMHSA's Concept of Trauma and Guidance for a Trauma-Informed Approach (2014)
"""

TRAUMA_INFORMED_PRINCIPLES = {
    "safety": {
        "name": "Safety",
        "description": "Throughout the organization, staff and the people they serve feel physically and psychologically safe",
        "keywords": ["safe", "safety", "secure", "protected", "comfort", "trust"]
    },
    "trustworthiness_transparency": {
        "name": "Trustworthiness and Transparency",
        "description": "Operations are conducted with transparency to build and maintain trust",
        "keywords": ["trust", "honest", "clear", "transparent", "reliable", "consistent"]
    },
    "peer_support": {
        "name": "Peer Support",
        "description": "Peer support and mutual self-help are key vehicles for establishing safety and hope",
        "keywords": ["peer", "support group", "community", "shared experience", "survivor"]
    },
    "collaboration_mutuality": {
        "name": "Collaboration and Mutuality",
        "description": "Partnering and leveling of power differences between staff and clients",
        "keywords": ["collaborate", "partner", "together", "mutual", "shared decision"]
    },
    "empowerment_voice_choice": {
        "name": "Empowerment, Voice and Choice",
        "description": "Recognizing and building on strengths, fostering belief in resilience and recovery",
        "keywords": ["choice", "voice", "empower", "control", "decide", "autonomy", "self-advocacy"]
    },
    "cultural_historical_gender": {
        "name": "Cultural, Historical, and Gender Issues",
        "description": "Moving past cultural stereotypes and biases, offering culturally responsive services",
        "keywords": ["culture", "identity", "background", "gender", "historical", "responsive"]
    }
}

# The Four R's of Trauma-Informed Approach
FOUR_RS = {
    "realize": "Realize the widespread impact of trauma and understand potential paths for recovery",
    "recognize": "Recognize the signs and symptoms of trauma in clients, families, staff, and others",
    "respond": "Respond by fully integrating knowledge about trauma into policies, procedures, and practices",
    "resist": "Resist re-traumatization"
}

# Scenario Categories for Post-Sexual Assault Care
SCENARIO_CATEGORIES = {
    "immediate_followup": {
        "name": "Immediate Post-Forensic Exam Follow-Up",
        "description": "Medical prophylaxis, STI/HIV testing, follow-up appointments",
    },
    "mental_health": {
        "name": "Mental Health and Emotional Support",
        "description": "Anxiety, trauma counseling, sleep disturbance, intrusive memories",
       
    },
    "practical_social": {
        "name": "Practical and Social Needs",
        "description": "Housing, transportation, financial assistance",
        
    },
    "legal_advocacy": {
        "name": "Legal and Advocacy Navigation",
        "description": "Protection orders, reporting options, legal accompaniment",
      
    },
    "delayed_ambivalent": {
        "name": "Delayed or Ambivalent Follow-Up",
        "description": "Re-engagement after delay, addressing barriers",
        
    }
}

# Crisis indicators that requires immediate escalation
CRISIS_INDICATORS = [
    "suicide",
    "suicidal",
    "kill myself",
    "end my life",
    "want to die",
    "harm myself",
    "hurt myself",
    "self-harm",
    "cutting",
    "overdose",
    "no reason to live",
    "better off dead"
]

# Comprehensive referral categories
REFERRAL_CATEGORIES = {
    "medical": ["Primary care", "STI testing", "HIV testing", "Reproductive health", "Injury follow-up"],
    "mental_health": ["Trauma counseling", "Crisis intervention", "Psychiatric evaluation", "Substance use support"],
    "advocacy": ["Sexual assault advocacy", "Medical accompaniment", "Legal accompaniment", "Safety planning"],
    "legal": ["Legal advocacy", "Protection orders", "Victim compensation"],
    "social": ["Housing", "Financial assistance", "Transportation", "Food assistance"],
    "community": ["Peer support groups", "Culturally specific services"]
}
