# Practical Deep Research with CrewAI: Flow, Crews, Tasks, and Agents

This project shows the full power of CrewAI with all its bells and whistles. It uses Flow to control the execution logic, a Crew with multiple Agents, two parallel Tasks (main and secondary) using the same Agent, Agents using CrewAI Tools (`EXASearchTool` and `LimitedScrapeWebsiteTool`) and a custom-made plotting Tool, memory and knowledge management, a Task Guardrail, and execution tracing.

`LimitedScrapeWebsiteTool` is a wrapper around the original CrewAI `ScrapeWebsiteTool`. It truncates the returned content of `ScrapeWebsiteTool` to the `SCRAPE_MAX_CHARS` maximum character length. This enforces a hard upper bound on text entering the Large Language Model (LLM) from scraping, so huge PDF/webpage dumps cannot flood downstream task context. If large web pages or PDF's still cause context overflows, reduce the `SCRAPE_MAX_CHARS` value.

## About

This project automatically produces comprehensive reports on diverse topics. It rapidly gathers, verifies, and synthesizes information from across the internet, delivering reliable, fact-checked reports that meet tight deadlines and exacting standards, regardless of the subject matter. You can see an example Markdown report and its plots in the `EXAMPLE-renewable-energy` folder.

## Flow, Crews, Tasks, Agents

A Flow is optional in CrewAI. It defines the execution order and conditions. In this example, the Flow decides whether the deep research Crew is needed or not. Flows are constructed by annotations to regular Python functions, in this example in the `src/main.py` script.
These are the main decorators for state persistence and for connecting the different functions, or tasks, inside the Flow:

- `@persist()`: automatically persists the state of the Flow. It automatically saves and reloads a Flow's state between steps or runs, using `SQLiteFlowPersistence` by default to write the state to a local SQLite database in a user folder with the project name `CrewAI/ai-crewai-deep-research`.
- `@start()`: indicates the entry point of the Flow. This sets the first function to run.
- `@listen()`: marks a function as a listener for the output of another task in the Flow. Functions decorated with `@listen()` will be executed when the specified task emits an output.
- `@router()`: allows you to define conditional routing logic based on the output of a function.

You should always monitor your Flow, in order to identify issues early on, and generally keep an eye on the health of the system. This can easily be done by allowing for tracing. Look at the `kickoff()` function inside the `src/main.py` script. Create an instance of the Flow and set the `tracing` argument to `True`. Once you run the Flow, this records every step the Flow takes, so you can later see exactly how decisions were made and how Agents interacted. At the end of the execution, you will have 20 seconds to accept an invitation to see the execution trace on the CrewAI platform, where you can explore all tracing data. You can change the telemetry platform from the CrewAI cloud to another telemetry platform, such as Arize Phoenix.

### The Flow of this project

![alt text](https://github.com/user-attachments/assets/932e98fb-e72f-487c-b6b4-1bd56ed1bd18 "Flow diagram")

When deep research is required, it will first ask clarifying questions if needed. A Crew will then get executed and the results of the Crew execution will get summarized. The deep research Crew has the following structure:

![alt text](https://github.com/user-attachments/assets/febdb287-ca0f-4036-aef7-2378e6e8a4c0 "Deep research Crew")

In CrewAI, Tasks (in the following diagram in white color) describe the work and expected output, while Agents (in black color with the agent symbol next to them) are the autonomous executors assigned to carry out those Tasks using their tools, role, and reasoning. Multiple Tasks can use the same Agent by giving the Agent different guidance.

![alt text](https://github.com/user-attachments/assets/db645f1d-e4a9-42c5-a70c-83a0ac623780 "Tasks Agents diagram")

## Required API keys for this example

You need an OpenAI API key for this example. [Get your OpenAI API key here](https://platform.openai.com/login).
You also need an Exa API key for this example. [Get your free Exa API key here](https://exa.ai/).
Insert both API keys into the `.env.example` file and then rename this file to just `.env` (remove the ".example" ending).

## Creating the plot flow diagram

This will take some time to generate. The result will be shown in your web browser.

```bash
python -c "from src.main import plot; plot()"
```

## Running this example

```bash
python -m src.main
```

### Example prompts

If you just use a simple prompt like

```
Hello!
```

which does not require further information, then deep research should not be triggered.

However, if you ask a more complex question like the following, then deep research should be triggered.

```
How has the share of renewable energy in total electricity generation changed from 2018 to 2023 in Germany and Spain? Use official or widely recognized public datasets, clearly note any provisional values, show the annual percentages in a table, calculate the total change in percentage points, and briefly explain the main reasons for the change. Prefer national grid/statistical sources, Eurostat, Ember, or IEA data.
```

The final result will be a report in the form of a Markdown file called `report.md` and a folder called `plots` with graphs created by the custom plot tool, if any suitable data can be plotted.

### Prevent context window overflow errors

If your executions fail because of context window overflow errors caused by too much history from pervious executions, then you can just delete the user folder with the project name `CrewAI/ai-crewai-deep-research`. This will reset this project. Alternatively, you can also stop carrying old run memory into new runs by removing the fixed `id` in the `kickoff()` function of the `src/main.py` script.
