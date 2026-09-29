import from graph.sample { sample_graph }
import from graph.walkers { TaskContext }

with entry:__main__ {
    brain = sample_graph();
    print("JacBrain: synthetic transient graph; no compiler validation is claimed.");
    context = brain spawn TaskContext(task_id="task", project_id="sample", jac_version="0.37.23");
    for item in context.matches {
        print(f"{item.evidence_id}: {item.content}");
    }
}
