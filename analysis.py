import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import database
from pathlib import Path
import os

OUTPUT_DIR = Path("outputs")
GRAPHS_DIR = OUTPUT_DIR / "graphs"

def ensure_dirs():
    GRAPHS_DIR.mkdir(parents=True, exist_ok=True)

def load_data():
    conn = database.get_connection()
    # Join courses, sections, evaluations
    query = """
        SELECT 
            c.filename, c.source, 
            s.section_index, 
            e.rubric1, e.rubric2, e.rubric3, e.rubric4, e.rubric5, e.rubric6, e.rubric7
        FROM evaluations e
        JOIN sections s ON e.section_id = s.id
        JOIN courses c ON s.course_id = c.id
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def generate_radar_chart(df: pd.DataFrame, filename: str):
    """Generate radar chart for a single course (average rubrics)."""
    # Filter for the specific course filename
    course_df = df[df['filename'] == filename]
    if course_df.empty:
        return

    # Calculate mean for each rubric
    categories = ['Goal Focus', 'Readability', 'Clarity', 'Prerequisites', 'Fluidity', 'Examples (Conc)', 'Examples (Cohere)']
    rubrics = ['rubric1', 'rubric2', 'rubric3', 'rubric4', 'rubric5', 'rubric6', 'rubric7']
    
    values = course_df[rubrics].mean().values.tolist()
    if not values or np.isnan(values).any():
        return
        
    values += values[:1] # Close the loop
    
    angles = [n / float(len(categories)) * 2 * np.pi for n in range(len(categories))]
    angles += angles[:1]
    
    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
    ax.plot(angles, values, linewidth=1, linestyle='solid')
    ax.fill(angles, values, 'b', alpha=0.1)
    
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories)
    ax.set_yticks([2, 4, 6, 8, 10])
    ax.set_ylim(0, 10)
    
    plt.title(f"Course Analysis: {filename}")
    plt.tight_layout()
    
    safe_name = filename.replace(".pdf", "").replace(" ", "_")
    out_path = GRAPHS_DIR / f"{safe_name}_radar.png"
    plt.savefig(out_path)
    plt.close()
    print(f"Generated radar chart: {out_path}")

def generate_source_boxplot(df: pd.DataFrame):
    """Generate boxplot comparing sources."""
    if df.empty or 'source' not in df.columns:
        return

    # Melt dataframe to long format for boxplot
    rubrics = ['rubric1', 'rubric2', 'rubric3', 'rubric4', 'rubric5', 'rubric6', 'rubric7']
    long_df = df.melt(id_vars=['source'], value_vars=rubrics, var_name='Rubric', value_name='Score')
    
    plt.figure(figsize=(12, 6))
    long_df.boxplot(column='Score', by='source', grid=False)
    plt.title('Score Distribution by Source')
    plt.suptitle('') # Suppress default title
    plt.ylabel('Score (1-10)')
    plt.xlabel('Source')
    
    out_path = GRAPHS_DIR / "source_comparison_boxplot.png"
    plt.savefig(out_path)
    plt.close()
    print(f"Generated boxplot: {out_path}")

def generate_heatmap(df: pd.DataFrame):
     # Pivot table: Index=Filename, Columns=Rubric, Values=Mean Score
    rubrics = ['rubric1', 'rubric2', 'rubric3', 'rubric4', 'rubric5', 'rubric6', 'rubric7']
    pivot = df.groupby('filename')[rubrics].mean()
    
    if pivot.empty:
        return

    plt.figure(figsize=(10, 8))
    plt.imshow(pivot.values, cmap='RdYlGn', aspect='auto', vmin=1, vmax=10)
    plt.colorbar(label='Score')
    
    categories = ['Goal Focus', 'Readability', 'Clarity', 'Prerequisites', 'Fluidity', 'Examples (Conc)', 'Examples (Cohere)']
    plt.xticks(range(len(categories)), categories, rotation=45)
    plt.yticks(range(len(pivot.index)), pivot.index)
    
    plt.title("Course Weakness Heatmap")
    plt.tight_layout()
    
    out_path = GRAPHS_DIR / "course_heatmap.png"
    plt.savefig(out_path)
    plt.close()
    print(f"Generated heatmap: {out_path}")

def run_analysis():
    ensure_dirs()
    print("Loading data...")
    df = load_data()
    
    if df.empty:
        print("No evaluation data found.")
        return

    print("Generating course-level radar charts...")
    for filename in df['filename'].unique():
        generate_radar_chart(df, filename)
        
    print("Generating aggregated plots...")
    generate_source_boxplot(df)
    generate_heatmap(df)
    
    # Save raw aggregates
    agg_path = OUTPUT_DIR / "aggregates.csv"
    df.groupby('filename').mean(numeric_only=True).to_csv(agg_path)
    print(f"Saved aggregates to {agg_path}")
