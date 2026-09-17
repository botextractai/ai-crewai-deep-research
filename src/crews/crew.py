import os
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import EXASearchTool, TavilySearchTool
from src.tools.chart_generator_tool import ChartGeneratorTool
from src.tools.limited_scrape_website_tool import LimitedScrapeWebsiteTool
from src.utils import get_exa_api_key, get_exa_base_url, get_tavily_api_key, get_search_provider, get_research_async_enabled

# import the guardrail
from src.crews.guardrails.guardrails import write_report_guardrail

# import the knoledge (user preferences)
from crewai.knowledge.source.text_file_knowledge_source import TextFileKnowledgeSource

# set the API key for the configured search provider
if get_search_provider() != "tavily":
    exa_key = get_exa_api_key()
    if exa_key:
        os.environ["EXA_API_KEY"] = exa_key


def _get_search_tool():
    """Return the configured search tool based on SEARCH_PROVIDER env var."""
    provider = get_search_provider()
    if provider == "tavily":
        api_key = get_tavily_api_key()
        if not api_key:
            raise ValueError("TAVILY_API_KEY must be set when SEARCH_PROVIDER=tavily")
        os.environ["TAVILY_API_KEY"] = api_key
        return TavilySearchTool()
    # default to Exa
    return EXASearchTool(
        base_url=get_exa_base_url(),
        summary=True,
        content=False,
    )

@CrewBase
class ParallelDeepResearchCrew:
    """ParallelDeepResearchCrew crew"""
    
    @agent
    def research_planner(self) -> Agent:
        return Agent(
            config=self.agents_config["research_planner"],
            llm='gpt-5.4',
            verbose=True
        )
    
    @agent
    def topic_researcher(self) -> Agent:
        return Agent(
            config=self.agents_config["topic_researcher"],
            tools=[
                _get_search_tool(),
                LimitedScrapeWebsiteTool(),
            ],
            llm='gpt-5.4-mini',
            verbose=True
        )

    @agent
    def fact_checker(self) -> Agent:
        return Agent(
            config=self.agents_config["fact_checker"],
            tools=[
                _get_search_tool(),
                LimitedScrapeWebsiteTool(),
            ],
            llm='gpt-5.4-mini',
            verbose=True
        )
    
    @agent
    def report_writer(self) -> Agent:
        return Agent(
            config=self.agents_config["report_writer"],
            tools=[ChartGeneratorTool()],
            llm='gpt-5.4',
            verbose=True
        )
    
    @task
    def create_research_plan(self) -> Task:
        return Task(
            config=self.tasks_config["create_research_plan"],
            llm='gpt-5.4',
        )
    
    @task
    def research_main_topics(self) -> Task:
        return Task(
            config=self.tasks_config["research_main_topics"],
            async_execution=get_research_async_enabled(),
        )
    
    @task
    def research_secondary_topics(self) -> Task:
        return Task(
            config=self.tasks_config["research_secondary_topics"],
            async_execution=get_research_async_enabled(),
        )
    
    @task
    def validate_main_topics(self) -> Task:
        return Task(
            config=self.tasks_config["validate_main_topics"],
        )
    
    @task
    def validate_secondary_topics(self) -> Task:
        return Task(
            config=self.tasks_config["validate_secondary_topics"],
        )
    
    @task
    def write_final_report(self) -> Task:
        return Task(
            config=self.tasks_config["write_final_report"],
            # add the guardrail
            guardrails=[write_report_guardrail],
            markdown=True,
            output_file='report.md'
        )
    
    # define the crew
    @crew
    def crew(self) -> Crew:
        """Creates the ParallelDeepResearchCrew crew"""
        return Crew(
            agents=self.agents,  # automatically created by the @agent decorator
            tasks=self.tasks,  # automatically created by the @task decorator
            # define the sequential process
            process=Process.sequential,
            # set the memory to True so the crew remembers previous interactions
            memory=True,
            verbose=True,
            # add the user preferences knowledge source (might not be required, dependent on the use case)
            knowledge_sources=[TextFileKnowledgeSource(
                file_paths=["user_preferences.txt"]
            )]
        )
