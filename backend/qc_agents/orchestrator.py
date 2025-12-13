import logging
from typing import Dict, Any, Optional
from datetime import datetime
from .commitment_detector import CommitmentDetectorAgent
from .conversion_pathfinder import ConversionPathfinderAgent
from .excellence_replicator import ExcellenceReplicatorAgent

logger = logging.getLogger(__name__)

class QCAgentOrchestrator:
    """
    Orchestrates the execution of all 3 QC agents and aggregates results
    """
    
    def __init__(self, db, api_key: str):
        self.db = db
        self.api_key = api_key
        self.agents = {}
    
    async def initialize_agents(self, user_id: str):
        """Load agent configurations and initialize agents"""
        try:
            # Fetch QC agent configs for this user
            configs = await self.db.qc_agent_config.find({'user_id': user_id}).to_list(10)
            
            # If no configs exist, use defaults with API key
            if not configs:
                logger.info(f"No QC agent configs found, using defaults with API key")
                
                # Get user's preferred QC model from preferences
                user_prefs = await self.db.user_preferences.find_one({
                    'user_id': user_id,
                    'type': 'qc_config'
                })
                preferred_model = user_prefs.get('model', 'gpt-4o') if user_prefs else 'gpt-4o'
                logger.info(f"Using QC model: {preferred_model}")
                
                default_config = {
                    'llm_provider': 'openai',
                    'llm_model': preferred_model,
                    'enabled': True,
                    'api_key': self.api_key  # Pass API key to agents
                }
                configs = [
                    {**default_config, 'agent_type': 'commitment_detector'},
                    {**default_config, 'agent_type': 'conversion_pathfinder'},
                    {**default_config, 'agent_type': 'excellence_replicator'}
                ]
            else:
                # Add API key to existing configs
                for config in configs:
                    config['api_key'] = self.api_key
            
            # Initialize each agent
            for config in configs:
                agent_type = config['agent_type']
                
                if not config.get('enabled', True):
                    logger.info(f"QC Agent {agent_type} is disabled, skipping")
                    continue
                
                if agent_type == 'commitment_detector':
                    self.agents['commitment_detector'] = CommitmentDetectorAgent(config)
                elif agent_type == 'conversion_pathfinder':
                    self.agents['conversion_pathfinder'] = ConversionPathfinderAgent(config)
                elif agent_type == 'excellence_replicator':
                    self.agents['excellence_replicator'] = ExcellenceReplicatorAgent(config)
            
            logger.info(f"✅ Initialized {len(self.agents)} QC agents for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing QC agents: {e}")
            return False
    
    async def analyze_call(self, 
                          call_id: str,
                          user_id: str,
                          transcript: str,
                          metadata: Dict[str, Any],
                          lead_id: Optional[str] = None,
                          agent_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Run all QC agents on a call and aggregate results
        
        Args:
            call_id: Call identifier
            user_id: User who owns this call
            transcript: Full call transcript
            metadata: Call metadata (duration, timestamps, etc.)
            lead_id: Optional lead ID to update
            agent_id: Agent ID that handled this call
        
        Returns:
            Complete QC analysis results
        """
        try:
            # Initialize agents if not already done
            if not self.agents:
                await self.initialize_agents(user_id)
            
            call_data = {
                'transcript': transcript,
                'metadata': metadata
            }
            
            # Run all agents in parallel (or sequentially for now)
            results = {}
            
            # Agent 1: Commitment Detector
            if 'commitment_detector' in self.agents:
                logger.info(f"🔍 Running Commitment Detector on call {call_id}")
                commitment_result = await self.agents['commitment_detector'].analyze(call_data)
                results['commitment_analysis'] = commitment_result
            
            # Agent 2: Conversion Pathfinder
            if 'conversion_pathfinder' in self.agents:
                logger.info(f"🗺️  Running Conversion Pathfinder on call {call_id}")
                conversion_result = await self.agents['conversion_pathfinder'].analyze(call_data)
                results['conversion_analysis'] = conversion_result
            
            # Agent 3: Excellence Replicator
            if 'excellence_replicator' in self.agents:
                logger.info(f"⭐ Running Excellence Replicator on call {call_id}")
                excellence_result = await self.agents['excellence_replicator'].analyze(call_data)
                results['excellence_analysis'] = excellence_result
            
            # Aggregate overall scores
            aggregated_scores = self._aggregate_scores(results)
            
            # Generate final recommendations
            final_recommendations = self._aggregate_recommendations(results)
            
            # Prepare final analysis document
            analysis_doc = {
                'id': f"qc_{call_id}",
                'user_id': user_id,
                'call_id': call_id,
                'lead_id': lead_id,
                'agent_id': agent_id,
                **results,
                'aggregated_scores': aggregated_scores,
                'recommendations': final_recommendations,
                'created_at': datetime.utcnow()
            }
            
            # Store in database
            insert_result = await self.db.call_analytics.insert_one(analysis_doc.copy())
            logger.info(f"✅ QC analysis stored for call {call_id}")
            
            # Update lead with scores if lead_id provided
            if lead_id:
                await self._update_lead_scores(lead_id, aggregated_scores)
            
            # Remove MongoDB ObjectId before returning (not JSON serializable)
            if '_id' in analysis_doc:
                del analysis_doc['_id']
            
            # Convert datetime to ISO string for JSON serialization
            if 'created_at' in analysis_doc:
                analysis_doc['created_at'] = analysis_doc['created_at'].isoformat()
            
            return analysis_doc
            
        except Exception as e:
            logger.error(f"Error in QC orchestrator for call {call_id}: {e}")
            return {
                'error': str(e),
                'call_id': call_id,
                'recommendations': ['Manual review required due to analysis error']
            }
    
    def _aggregate_scores(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Aggregate scores from all agents"""
        scores = {}
        
        # Extract scores from each agent
        commitment = results.get('commitment_analysis', {})
        conversion = results.get('conversion_analysis', {})
        excellence = results.get('excellence_analysis', {})
        
        # Commitment scores
        scores['commitment_score'] = commitment.get('commitment_analysis', {}).get('linguistic_score', 50)
        scores['show_up_probability'] = commitment.get('show_up_probability', 50)
        scores['risk_level'] = commitment.get('risk_level', 'medium')
        
        # Conversion scores
        funnel_analysis = conversion.get('funnel_analysis', {})
        scores['conversion_score'] = funnel_analysis.get('funnel_completion', 50)
        scores['qualification_level'] = conversion.get('framework_scores', {}).get('bant', {}).get('qualification_level', 'unknown')
        
        # Excellence scores
        scores['excellence_score'] = excellence.get('excellence_score', 50)
        
        # Overall quality score (weighted average)
        overall = (
            scores['commitment_score'] * 0.35 +
            scores['conversion_score'] * 0.35 +
            scores['excellence_score'] * 0.30
        )
        scores['overall_quality_score'] = round(overall)
        
        return scores
    
    def _aggregate_recommendations(self, results: Dict[str, Any]) -> list:
        """Aggregate recommendations from all agents"""
        all_recommendations = []
        
        # Get recommendations from each agent
        commitment = results.get('commitment_analysis', {})
        conversion = results.get('conversion_analysis', {})
        excellence = results.get('excellence_analysis', {})
        
        # Action items from commitment
        action_items = commitment.get('action_items', [])
        all_recommendations.extend(action_items)
        
        # Recommendations from conversion
        conv_recs = conversion.get('recommendations', [])
        all_recommendations.extend(conv_recs)
        
        # Recommendations from excellence
        exc_recs = excellence.get('recommendations', [])
        all_recommendations.extend(exc_recs)
        
        # Deduplicate and prioritize
        unique_recommendations = list(dict.fromkeys(all_recommendations))
        
        return unique_recommendations[:10]  # Top 10
    
    async def _update_lead_scores(self, lead_id: str, scores: Dict[str, Any]):
        """Update lead record with QC scores"""
        try:
            update_data = {
                'commitment_score': scores.get('commitment_score'),
                'conversion_score': scores.get('conversion_score'),
                'excellence_score': scores.get('excellence_score'),
                'show_up_probability': scores.get('show_up_probability'),
                'updated_at': datetime.utcnow(),
                'last_contact': datetime.utcnow()
            }
            
            await self.db.leads.update_one(
                {'id': lead_id},
                {
                    '$set': update_data,
                    '$inc': {'total_calls': 1}
                }
            )
            
            logger.info(f"✅ Updated lead {lead_id} with QC scores")
            
        except Exception as e:
            logger.error(f"Error updating lead {lead_id} with scores: {e}")
