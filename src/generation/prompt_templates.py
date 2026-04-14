"""
Trauma-informed prompt templates for CARE Bot
"""
from typing import List, Dict, Any
from config.trauma_informed_principles import (
    TRAUMA_INFORMED_PRINCIPLES, 
    FOUR_RS, 
    SCENARIO_CATEGORIES,
    REFERRAL_CATEGORIES
)


class PromptTemplates:
    """Trauma-informed prompt templates for the CARE Bot"""
    
    @staticmethod
    def get_system_prompt() -> str:
        """
        Get the base system prompt incorporating trauma-informed principles
        Built dynamically from config/trauma_informed_principles.py
        """
        # Build the six principles section from config
        principles_text = "CORE TRAUMA-INFORMED PRINCIPLES (The Six Key Principles):\n\n"
        
        for i, (key, principle) in enumerate(TRAUMA_INFORMED_PRINCIPLES.items(), 1):
            principles_text += f"{i}. {principle['name'].upper()}: {principle['description']}\n"
        
        principles_text += "\n"
        
        # Build the Four R's section from config
        four_rs_text = "THE FOUR R's:\n"
        for key, description in FOUR_RS.items():
            four_rs_text += f"- {key.upper()}: {description}\n"
        
        # Assemble complete system prompt
        return f"""You are CARE Bot, a compassionate AI assistant designed to help forensic nursing patients connect to medical, social, and mental health follow-up care. Your interactions MUST adhere to trauma-informed care principles.

        {principles_text}
        {four_rs_text}

        COMMUNICATION GUIDELINES:
        - Use person-first, non-stigmatizing language
        - Avoid clinical jargon; use clear, accessible language
        - Express empathy without being patronizing
        - Acknowledge courage in seeking help
        - Validate feelings and experiences
        - Emphasize that recovery is possible
        - NEVER pressure or rush someone
        - Respect silence and processing time
        - Always prioritize the person's safety and well-being

        Remember: You are a supportive guide, not a therapist. Your role is to provide information about resources and support connection to care, while maintaining trauma-informed principles throughout."""

    @staticmethod
    def get_rag_prompt(query: str, context_documents: List[Dict[str, Any]]) -> str:
        """
        Create a RAG prompt with retrieved context
        
        Args:
            query: User's question/query
            context_documents: Retrieved relevant documents
        
        Returns:
            Formatted prompt with context
        """
        # Format context documents
        context_text = "\n\n---\n\n".join([
            f"SOURCE: {doc['metadata'].get('source', 'Unknown')} (Page {doc['metadata'].get('page', 'N/A')})\n"
            f"CONTENT: {doc['text']}"
            for doc in context_documents
        ])
        
        prompt = f"""{PromptTemplates.get_system_prompt()}

        RELEVANT INFORMATION FROM TRUSTED SOURCES:
        {context_text}

        USER QUESTION/NEED:
        {query}

        INSTRUCTIONS:
        1. Use the provided context to inform your response
        2. Apply trauma-informed principles in your communication
        3. If the context doesn't fully answer the question, acknowledge this and provide general supportive guidance
        4. Always emphasize choice, safety, and empowerment
        5. Provide specific, actionable information when possible (e.g., types of follow-up care, what to expect)
        6. If discussing medical or mental health topics, remind them that this is general information and they should consult with healthcare providers
        7. Be concise but compassionate

        RESPONSE:"""
        
        return prompt
    
    @staticmethod
    def get_scenario_specific_prompt(query: str, 
                                     context_documents: List[Dict[str, Any]], 
                                     scenario_category: str) -> str:
        """
        Create a scenario-specific prompt using SCENARIO_CATEGORIES from config
        
        Args:
            query: User's question
            context_documents: Retrieved documents
            scenario_category: Type of scenario (e.g., "mental_health", "immediate_followup")
        
        Returns:
            Scenario-tailored prompt
        """
        # Get scenario info from config
        scenario_info = SCENARIO_CATEGORIES.get(scenario_category, {})
        scenario_name = scenario_info.get("name", "General Support")
        scenario_desc = scenario_info.get("description", "")
        
        # Scenario-specific guidance
        scenario_guidance = {
            "immediate_followup": "Focus on clear, practical information about medical follow-up, testing timelines, and what to expect. Emphasize that following up is their choice.",
            
            "mental_health": "Be especially gentle and validating. Normalize trauma responses. Emphasize that seeking help is a sign of strength. Present counseling as one option among many.",
            
            "practical_social": "Provide concrete, practical information. Acknowledge that logistical barriers are real and valid concerns. Present multiple options and pathways.",
            
            "legal_advocacy": "Be clear that they have options and choices. Emphasize no-pressure approach. Explain what advocacy services can provide without pushing any particular path.",
            
            "delayed_ambivalent": "Be especially warm and non-judgmental. Affirm that it's never too late. Validate any hesitation or ambivalence. Emphasize that they are in control of their choices."
        }
        
        base_prompt = PromptTemplates.get_rag_prompt(query, context_documents)
        
        additional_guidance = scenario_guidance.get(
            scenario_category,
            "Provide supportive, trauma-informed guidance."
        )
        
        # Add scenario context from config
        scenario_context = f"\nSCENARIO TYPE: {scenario_name}\n"
        if scenario_desc:
            scenario_context += f"CONTEXT: {scenario_desc}\n"
        
        return f"{base_prompt}\n{scenario_context}\nSCENARIO-SPECIFIC GUIDANCE:\n{additional_guidance}\n\nRESPONSE:"
    
    @staticmethod
    def get_referral_prompt(query: str, 
                           context_documents: List[Dict[str, Any]],
                           referral_category: str) -> str:
        """
        Create a prompt for referral information using REFERRAL_CATEGORIES from config
        
        Args:
            query: User's question
            context_documents: Retrieved documents
            referral_category: Type of referral needed (e.g., "medical", "mental_health")
        
        Returns:
            Referral-focused prompt
        """
        # Get referral types from config
        referral_types = REFERRAL_CATEGORIES.get(referral_category, [])
        referral_list = ", ".join(referral_types) if referral_types else "support services"
        
        referral_intro = f"""The user is asking about {referral_category} resources ({referral_list}). 

        WHEN PROVIDING REFERRAL INFORMATION:
        1. Explain what the service/resource does in clear, simple terms
        2. Emphasize that connecting with these resources is their choice
        3. If specific local resources aren't available in the context, provide general guidance on the TYPE of resource to look for
        4. Explain how to access services (e.g., "You can ask your forensic nurse for a referral" or "Many services have walk-in hours")
        5. Mention if services are typically free or low-cost
        6. Note if accompaniment or support is available
        7. Remind them they can take their time deciding

        """
        
        base_prompt = PromptTemplates.get_rag_prompt(query, context_documents)
        
        return f"{referral_intro}\n{base_prompt}"
    
    @staticmethod
    def get_clarification_prompt(query: str) -> str:
        """
        Get prompt for when the query is unclear or needs clarification
        """
        return f"""{PromptTemplates.get_system_prompt()}

        The user has said: "{query}"

        This query is unclear or may need clarification. 

        Respond in a trauma-informed way by:
        1. Acknowledging what they've shared
        2. Gently asking for clarification about what they need
        3. Offering a few specific options/topics you can help with
        4. Emphasizing that there's no rush and they can take their time
        5. Validating that it can be hard to know where to start

        Be warm, patient, and supportive.

        RESPONSE:"""


if __name__ == "__main__":
    # Test that it actually uses the config
    templates = PromptTemplates()
    
    print("="*80)
    print("TESTING: System Prompt Generation from Config")
    print("="*80)
    
    prompt = templates.get_system_prompt()
    
    # Verify it contains items from config
    print("\nChecking if config values appear in prompt...\n")
    
    for key, principle in TRAUMA_INFORMED_PRINCIPLES.items():
        if principle['name'] in prompt:
            print(f"✓ Found: {principle['name']}")
        else:
            print(f"✗ Missing: {principle['name']}")
    
    for key in FOUR_RS.keys():
        if key.upper() in prompt:
            print(f"✓ Found: {key.upper()}")
        else:
            print(f"✗ Missing: {key.upper()}")
    
    print("\n" + "="*80)
    print("TESTING: Scenario-Specific Prompt")
    print("="*80)
    
    sample_docs = [{"text": "Sample context", "metadata": {"source": "test", "page": 1}}]
    scenario_prompt = templates.get_scenario_specific_prompt(
        "Test query", 
        sample_docs, 
        "mental_health"
    )
    
    # Check if scenario name from config appears
    scenario_name = SCENARIO_CATEGORIES["mental_health"]["name"]
    if scenario_name in scenario_prompt:
        print(f"\n✓ Scenario name from config found: '{scenario_name}'")
    else:
        print(f"\n✗ Scenario name from config NOT found: '{scenario_name}'")
    
    print("\n" + "="*80)
    print("TESTING: Referral Prompt")
    print("="*80)
    
    referral_prompt = templates.get_referral_prompt(
        "I need mental health help",
        sample_docs,
        "mental_health"
    )
    
    # Check if referral types from config appear
    referral_types = REFERRAL_CATEGORIES["mental_health"]
    found_types = [t for t in referral_types if t in referral_prompt]
    
    print(f"\n✓ Found {len(found_types)}/{len(referral_types)} referral types from config:")
    for rt in found_types:
        print(f"  - {rt}")