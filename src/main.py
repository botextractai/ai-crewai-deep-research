from pydantic import BaseModel
from crewai import LLM
from crewai.flow import Flow, listen, start, router, or_
from crewai.flow.persistence import persist
from src.crews.crew import ParallelDeepResearchCrew
import logging
import traceback

logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

# define the flow state as a Pydantic model
# the flow state is a group of variables that store the current state of the flow
class ResearchState(BaseModel):
    user_query: str = ""
    needs_research: bool = False
    research_report: str = ""
    final_answer: str = ""

# add persistence to the flow
# this saves the state of the flow and all executions into a database, so that the data persists across different executions
@persist()

class DeepResearchFlow(Flow[ResearchState]):
    # define the entry point
    @start()
    def start_conversation(self):
        """Entry point for the flow"""
        print("🔍 Deep Research Flow started")
        print(self.state.user_query)
        if self.state.user_query != "":
            print(f"I remember last time you wanted to know about {self.state.user_query}")
        self.state.user_query = input("\033[1;31m What would you like to know?\033[0m  \n>> \n")
        print(f"Query received: \"{self.state.user_query}\"")
    
    # define the router
    @router(start_conversation)
    def analyze_query(self):
        """Router: Should trigger research?"""
        print("🤔 Analyzing query complexity...")
        
        # write the prompt for the LLM to decide if the query is simple or requires research
        prompt = ("Analyze this query and respond with exactly one word: SIMPLE or RESEARCH\n\n"
                "SIMPLE: greetings, basic questions, well-known facts, context-based queries\n"
                "RESEARCH: complex topics requiring comprehensive investigation, current events, detailed analysis, multi-faceted questions\n\n"
                f"Query: \"{self.state.user_query}\"\n\n"
                "Response (one word only):")
        
        # define the llm for the decision
        llm = LLM(model="gpt-5.4-mini",)
        # call the llm and save the result
        decision = llm.call(messages=prompt)
        
        if "RESEARCH" in decision.upper():
            self.state.needs_research = True
            print("📚 Complex query detected - initiating research process")
            return "RESEARCH"
        else:
            print("💬 Simple query detected - providing direct answer")
            return "SIMPLE"
    
    # define the simple answer task (no research needed)
    @listen("SIMPLE")
    def simple_answer(self):
        """LLM: Direct answer for simple queries"""
        print("✨ Generating direct answer...")
        
        # write the missing part of the query for the LLM
        prompt = ("Provide a direct, helpful, and comprehensive answer to this query. "
                "Be informative but concise.\n\n"
                f"Query: \"{self.state.user_query}\"\n\n"
                "Answer:"
                )
        # set up the LLM
        llm = LLM(model="gpt-5.4-mini",)
        # call the llm with the prompt and save the result to the final_answer state variable
        self.state.final_answer = llm.call(messages=prompt)
    
    # define the clarification task (if research is needed)
    @listen("RESEARCH")
    def clarify_query(self):
        """LLM: Clarification before research"""
        print("🔍 Reviewing query for research clarity...")
        
        # write the prompt to decide if the query is clear enough
        prompt = ("Review this research query and determine if it's clear enough "
                 "for comprehensive research.\n\n"
                 "Ask a maximum of 2 concise clarification questions.\n"
                 "Respond in one of these formats:\n"
                 "- If clear enough (including with reasonable assumptions): \"PROCEED\"\n"
                 "- If clarification is required: \"CLARIFY: [up to 3 specific questions]\"\n\n"
                 f"Query: \"{self.state.user_query}\"\n\n"
                 "Response:"
                 )
        # define the llm and call it with the prompt
        llm = LLM(model="gpt-5.4-mini",)
        response = llm.call(messages=prompt)
        
        # if the query is not clear, ask the user for clarification
        if "PROCEED" not in response:
            clarification_needed = response.replace("CLARIFY:", "").strip()
            print(f"❓ \033[1;31m Clarification needed:\n\033[0m {clarification_needed}")
            additional_info = input("\033[1;31m Please provide more details: \n>> \n\033[0m")
            # update the user_query state variable with the additional information
            self.state.user_query += f"\n\nAdditional context: {additional_info}"
    
    # define the research execution task
    @listen("clarify_query")
    def execute_research(self):
        """execute the deep research crew"""
        print("🚀 Executing deep research crew...")
        print(f"🔍 Researching: \"{self.state.user_query}\"")
        
        # define the crew
        research_crew = ParallelDeepResearchCrew()
        
        crew_instance = research_crew.crew()
        logger.info(
            "Crew kickoff diagnostic | query_len=%s | agents=%s | tasks=%s",
            len(self.state.user_query or ""),
            [getattr(agent, "role", "unknown") for agent in crew_instance.agents],
            [getattr(task, "name", "unknown") for task in crew_instance.tasks],
        )
        logger.info(
            "Crew models/tools | agent_models=%s | tools=%s | task_async=%s",
            [getattr(agent, "llm", None) for agent in crew_instance.agents],
            [
                [getattr(tool, "name", tool.__class__.__name__) for tool in getattr(agent, "tools", [])]
                for agent in crew_instance.agents
            ],
            [getattr(task, "async_execution", None) for task in crew_instance.tasks],
        )
        
        try:
            # kickoff the crew with the user query as input
            result = crew_instance.kickoff(
                # use the value in the user_query state variable as the input
                inputs={"user_query": self.state.user_query}
            )
        except Exception as e:
            logger.error("Crew kickoff failed: %s", e)
            logger.error("Detailed traceback:\n%s", traceback.format_exc())
            raise
        
        # update the research_report state variable with the crew's output (use the `raw` attribute)
        self.state.research_report = result.raw
        
        print("✅ Research completed successfully!")
    
    # define the task to save and summarize the report
    @listen(execute_research)
    def save_report_and_summarize(self):
        """
        Summarize the final research report
        """
        # report.md is already saved by the write_final_report task output_file setting
        print("✅ Report available at report.md")
        
        # summarize the report
        # define the LLM and and write the prompt
        llm = LLM(model="gpt-5.4-mini")
        prompt = ("Summarize the following research report into a one paragraph, informative answer:\n\n"
                  f"Report: \"{self.state.research_report}\"\n\n"
                 )
        # update the final_answer state variable with the summary from the LLM call
        self.state.final_answer = ("This is a summary of the final answer:\n\n" 
                                    f"{llm.call(messages=prompt)}\n\n"
                                    "A full report has been saved to report.md."
                                    )
    
    # define the final answer task
    @listen(or_("simple_answer", "save_report_and_summarize"))
    def return_final_answer(self):
        """Return the final answer to the user"""
        print("📝 Final Answer:")
        print(f"📌 Original Query: \"{self.state.user_query}\"")
        print(f"{self.state.final_answer}")
        print("\n✨ Deep Research Flow completed!")

def kickoff():
    # instantiate the DeepResearchFlow with tracing enabled
    deep_research_flow = DeepResearchFlow(tracing=True)
    
    # kickoff the flow with a custom id to persist the state
    # the flow will use the persistent state (memory) from previous runs to continue the conversation
    # if no id is provided, the flow will start a new conversation and clear the persistent state (memory)
    deep_research_flow.kickoff(inputs={"id": "our-deep-research_flow"})

def plot():
    deep_research_flow = DeepResearchFlow()
    deep_research_flow.plot()

if __name__ == "__main__":
    kickoff()
