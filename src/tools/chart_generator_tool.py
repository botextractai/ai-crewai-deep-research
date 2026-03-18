import os
import matplotlib  # optional to force early import
matplotlib.use("agg")

# import packages needed for the custom tool
from crewai.tools import BaseTool
from crewai import LLM
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import json

class ChartGeneratorTool(BaseTool):
    name: str = "Create custom plots"
    description: str = ("This a tool for automatically creating custom plots based on a research result. "
                        "This tools automatically generates the plots from a text input, which should have fact checked information. "
                        "Pass the full validated information gathered so far as a string."
                        )
    attempt_count: int = 0
    allow_retry_after_empty_result: bool = False
    generated_plots_once: bool = False
    
    def _is_complete_chart_data(self, data: dict, x_axis: str, y_axis: str, hue: str | None) -> bool:
        if not isinstance(data, dict) or x_axis not in data or y_axis not in data:
            return False
        if not isinstance(data.get(x_axis), list) or not isinstance(data.get(y_axis), list):
            return False
        base_len = len(data.get(x_axis))
        if base_len == 0 or len(data.get(y_axis)) != base_len:
            return False
        if hue is not None:
            if hue not in data or not isinstance(data.get(hue), list) or len(data.get(hue)) != base_len:
                return False
        return True
    
    def _run(self, research: str) -> str:
        try:
            # allow exactly one successful generation run
            # a second attempt is only permitted when the first attempt produced zero plots
            if self.generated_plots_once:
                return (
                    "Plots were already generated in this run. "
                    "Do not call this tool again to avoid duplicates."
                )
            if self.attempt_count >= 1 and not self.allow_retry_after_empty_result:
                return (
                    "This tool can only be called once per run unless the first call produced no plots."
                )
            if self.attempt_count >= 2:
                return "Maximum chart generation attempts reached for this run."
            
            self.attempt_count += 1
            
            extraction_prompt = f"""
            You are an expert data visualization assistant. Analyze the provided research text and identify only the highest-value charts that clearly support the key findings.
            
            Quality rules (strict):
            - Return a maximum of 3 charts total.
            - Prefer 1-2 strong charts over many weak charts.
            - This tool should normally be used only once per report.
            - Do not create duplicate charts (same metric with only minor label or style differences).
            - Only suggest charts for clearly quantifiable data with reliable numbers.
            - Skip any chart if data is sparse, ambiguous, low-signal, or mostly qualitative.
            - Favor line/bar/scatter charts. Use pie charts only when showing simple part-to-whole with <= 6 categories.
            - If no clearly valuable chart exists, return [].
            
            For each chart, provide a JSON object with:
              - "chart_type" (string: choose from "line" for trends over time/continuous, "bar" for comparisons, "histogram" for distributions, "scatter" for relationships, "pie" for proportions)
              - "x_axis" (string: variable name for x-axis, e.g., "year", "category")
              - "y_axis" (string: variable name for y-axis, e.g., "value", "count")
              - "color" (string: optional variable for color grouping/hue, or null if not applicable)
              - "Title" (string: descriptive, insightful title that explains what the chart shows)
              - "data" (dictionary: keys matching x_axis, y_axis, and color variables; values as lists of extracted numerical/categorical data from the research)
            
            Ensure data is accurately extracted and formatted as lists. If a variable has multiple series (e.g., for color), include all in the data dictionary.
            Each selected chart should answer a distinct analytical question (trend, comparison, relationship, or distribution).
            
            If no quantifiable data suitable for meaningful visualization is present in the research, return an empty array [].
            
            Text:
            {research}
            
            Example output (return valid JSON only):
            [
              {{"chart_type": "line", "x_axis": "year", "y_axis": "funding_amount", "color": "sector", "Title": "AI Research Funding Trends by Sector", "data": {{"year": [2020, 2021, 2022], "funding_amount": [2.5, 3.8, 5.2], "sector": ["Healthcare", "Finance", "Tech"]}}}},
              {{"chart_type": "bar", "x_axis": "tool_name", "y_axis": "adoption_rate", "color": null, "Title": "Market Adoption Rates of AI Tools", "data": {{"tool_name": ["ToolA", "ToolB", "ToolC"], "adoption_rate": [45, 67, 23]}}}}
            ]
            
            Return only the JSON array, no additional text or explanations.
            """
            
            llm = LLM(model="gpt-5.4",)  # initialize the LLM instance
            llm_response = llm.call([{"role": "user", "content": extraction_prompt}])
            
            # clean the response to extract just the JSON part
            llm_response = llm_response.strip()
            if llm_response.startswith('```json'):
                llm_response = llm_response[7:]  # remove ```json
            if llm_response.endswith('```'):
                llm_response = llm_response[:-3]  # remove ```
            llm_response = llm_response.strip()
            
            # --- Step 2: Parse the LLM output ---
            charts_data = json.loads(llm_response)
            
            if not isinstance(charts_data, list) or len(charts_data) == 0:
                if self.attempt_count == 1:
                    self.allow_retry_after_empty_result = True
                    return (
                        "No information found in the research to visualize. "
                        "You may call this tool one more time with better structured numeric input."
                    )
                self.allow_retry_after_empty_result = False
                return "No information found in the research to visualize."
            
            # hard cap as a safety net to enforce quality over quantity
            charts_data = charts_data[:3]
            
            plots_created = []
            seen_signatures = set()
            
            # --- Step 3: Create plots for each chart ---
            for i, chart_info in enumerate(charts_data):
                try:
                    # extract chart configuration
                    chart_type = (chart_info.get("chart_type") or "").lower()
                    x_axis = chart_info.get("x_axis", "x")
                    y_axis = chart_info.get("y_axis", "y") 
                    title = chart_info.get("Title", f"Chart {i+1}")
                    hue = chart_info.get("color", None)
                    data = chart_info.get("data", {})
                    if hue in ("", "null", "none"):
                        hue = None
                    
                    if chart_type not in {"line", "bar", "column", "histogram", "scatter", "pie"}:
                        continue
                    if not self._is_complete_chart_data(data, x_axis, y_axis, hue):
                        continue
                    
                    # create DataFrame from the data
                    df = pd.DataFrame(data)
                    
                    if df.empty:
                        continue
                    
                    required_cols = [x_axis, y_axis] + ([hue] if hue else [])
                    # create charts only when complete rows are available (no missing values)
                    if df[required_cols].isna().any().any():
                        continue
                    
                    # de-duplicate equivalent chart requests in a single run
                    signature = (chart_type, x_axis, y_axis, hue, title.strip().lower())
                    if signature in seen_signatures:
                        continue
                    seen_signatures.add(signature)
                    
                    # create the plot
                    plt.figure(figsize=(10, 6))
                    
                    if chart_type == "line":
                        if df.shape[0] < 3 or not pd.api.types.is_numeric_dtype(df[y_axis]):
                            plt.close()
                            continue
                        sns.lineplot(data=df, x=x_axis, y=y_axis, marker="o", hue=hue)
                    elif chart_type in ["bar", "column"]:
                        if df.shape[0] < 2 or not pd.api.types.is_numeric_dtype(df[y_axis]):
                            plt.close()
                            continue
                        sns.barplot(data=df, x=x_axis, y=y_axis, hue=hue)
                    elif chart_type == "histogram":
                        if df.shape[0] < 10 or not pd.api.types.is_numeric_dtype(df[y_axis]):
                            plt.close()
                            continue
                        plt.hist(df[y_axis], bins=10, alpha=0.7, hue=hue)
                        plt.xlabel(y_axis)
                        plt.ylabel("Frequency")
                    elif chart_type == "scatter":
                        if df.shape[0] < 3 or not pd.api.types.is_numeric_dtype(df[y_axis]):
                            plt.close()
                            continue
                        # default to scatter plot
                        sns.scatterplot(data=df, x=x_axis, y=y_axis, hue=hue)
                    elif chart_type == "pie":
                        # for pie chart, assume y_axis is values, x_axis is labels
                        if (
                            df.shape[0] < 2
                            or df.shape[0] > 6
                            or not pd.api.types.is_numeric_dtype(df[y_axis])
                            or (df[y_axis] <= 0).any()
                        ):
                            plt.close()
                            continue
                        plt.pie(df[y_axis], labels=df[x_axis], autopct='%1.1f%%', startangle=90)
                        plt.title(title)
                        plt.axis('equal')  # equal aspect ratio ensures that pie is drawn as a circle
                    
                    plt.title(title)
                    plt.xticks(rotation=45)
                    plt.tight_layout()
                    
                    # --- Step 4: Save the plot ---
                    os.makedirs("plots", exist_ok=True)
                    filename = f"plots/plot_{i+1}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                    plt.savefig(filename, dpi=300, bbox_inches='tight')
                    plt.close()
                    
                    plots_created.append(filename)
                
                except Exception as e:
                    print(f"Error creating chart {i+1}: {str(e)}")
                    continue
            
            if plots_created:
                self.generated_plots_once = True
                self.allow_retry_after_empty_result = False
                return f"Successfully created {len(plots_created)} plots: {', '.join(plots_created)}"
            else:
                if self.attempt_count == 1:
                    self.allow_retry_after_empty_result = True
                    return (
                        "No plots could be created from the extracted data. "
                        "You may call this tool one more time with better structured numeric input."
                    )
                self.allow_retry_after_empty_result = False
                return "No plots could be created from the extracted data."
        
        except json.JSONDecodeError as e:
            return f"Error parsing LLM response as JSON: {str(e)}"
        except Exception as e:
            return f"Error generating smart plot: {str(e)}"
