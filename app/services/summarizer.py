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

def get_summarized_report(category_name: str, tasks: List[Task]) -> str:
    """Generates a concise ranked summary."""
    compute_tfidf(tasks)
    # Sort by importance
    ranked_tasks = sorted(tasks, key=lambda x: x.importanceScore, reverse=True)
    
    # Take top 5 tasks for summary
    top_tasks = ranked_tasks[:5]
    
    summary_lines = [f"### {category_name} - Weekly Summary"]
    if not top_tasks:
        summary_lines.append("No active tasks or updates found in the last 7 days.")
    else:
        for task in top_tasks:
            status_icon = "[DONE]" if "Done" in task.taskStatus else "[PNDG]"
            summary_lines.append(f"- {status_icon} **{task.taskSubject}** ({task.taskStatus})")
            if task.followUpComments:
                latest = task.followUpComments[0][:100] + "..." if len(task.followUpComments[0]) > 100 else task.followUpComments[0]
                summary_lines.append(f"  *Latest update:* {latest}")
    
    return "\n".join(summary_lines)
