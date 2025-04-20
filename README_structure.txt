# README_structure.txt (excerpt)

- system_prompt_template_allcommit.j2: Feature extension template for 'allcommit' (extends main style). Now instructs: "After each step which does a change, perform git commit with a clear message describing what was changed."
- janito/agent/templates/profiles/system_prompt_template_base.j2: Updated to instruct: "After each step which does a change, perform git commit. Check the git diff and summarize the changes in the commit message."

All commit-related instructions now explicitly require a git commit after each step which does a change.