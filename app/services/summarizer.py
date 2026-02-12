import math
import re
from typing import List
from ..models.schemas import Task

def tokenize(text: str) -> List[str]:
    """Simple tokenizer that converts text to lower case and removes non-alphanumeric chars."""
    if not text:
        return []
    tokens = re.findall(r'\w+', text.lower())
    return [t for t in tokens if len(t) > 2]

def compute_tfidf(tasks: List[Task]):
    """
    Computes TF-IDF scores for tasks.
    Treats each task as a document.
    """
    if not tasks:
        return

    documents = []
    for task in tasks:
        text = f"{task.taskSubject} {' '.join(task.followUpComments)}"
        documents.append(tokenize(text))

    num_docs = len(documents)
    if num_docs == 0:
        return

    # Count Document Frequency (DF)
    all_words = set(word for doc in documents for word in doc)
    df = {}
    for word in all_words:
        count = sum(1 for doc in documents if word in doc)
        df[word] = count

    # Compute TF-IDF for each task
    for i, task in enumerate(tasks):
        doc = documents[i]
        if not doc:
            task.importanceScore = 0.0
            continue
            
        tf = {}
        for word in doc:
            tf[word] = tf.get(word, 0) + 1
            
        score = 0.0
        for word, count in tf.items():
            idf_val = math.log(num_docs / df[word]) if df[word] > 0 else 0
            score += count * idf_val
        
        task.importanceScore = round(score / len(doc), 4) if doc else 0.0

def get_summarized_report(category_name: str, tasks: List[Task], detail_level: str = "short", time_window_label: str = "Last 7 Days") -> str:
    """Generates a ranked summary with configurable detail level."""
    compute_tfidf(tasks)
    # Sort by importance
    ranked_tasks = sorted(tasks, key=lambda x: x.importanceScore, reverse=True)
    
    # Take top 5 tasks for summary
    top_tasks = ranked_tasks[:5]
    
    summary_lines = [f"### {category_name} - Summary ({time_window_label})"]
    if not top_tasks:
        summary_lines.append(f"No active tasks or updates found in {time_window_label.lower()}.")
    else:
        for task in top_tasks:
            summary_lines.append(get_single_task_summary(task, detail_level))
    
    return "\n".join(summary_lines)

def get_single_task_summary(task: Task, detail_level: str = "short") -> str:
    """Generates a summary for a single task."""
    status_icon = "[DONE]" if "Done" in task.taskStatus else "[PNDG]"
    summary = f"- {status_icon} **{task.taskSubject}** (ID: {task.taskId}, Status: {task.taskStatus})"
    
    if not task.followUpComments:
        return summary
        
    if detail_level == "short":
        # Just the latest comment, truncated
        latest = task.followUpComments[0][:150] + "..." if len(task.followUpComments[0]) > 150 else task.followUpComments[0]
        summary += f"\n  *Latest update:* {latest}"
    else:
        # Detailed: combine all comments or first few in detail
        summary += "\n  *Recent Updates:*"
        for i, comment in enumerate(task.followUpComments[:5]): # Show up to 5 comments in detail
            summary += f"\n    {i+1}. {comment}"
        if len(task.followUpComments) > 5:
            summary += f"\n    ... and {len(task.followUpComments) - 5} more updates."
            
    return summary
