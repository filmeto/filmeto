---
name: react_skill_observation
description: Skill execution observation prompt for ReAct loop
version: 1.0
---
[SKILL RESULT ANALYSIS REQUIRED]

You have just received the result from a skill execution. BEFORE deciding to give a final response, you MUST complete the following analysis:

1. **Analyze the skill output**: What did the skill produce? Is it complete?

2. **Compare against your original task**: Review the user's instruction that you were trying to fulfill. Does this skill output directly address what was asked?

3. **Check completion status**:
   - If the task is NOT fully complete → You MUST call another skill or process the result
   - If the result needs transformation/formatting → Call a processing skill
   - If you need to verify the result → Call a validation skill
   - Only if the task IS 100% complete and ready → Use final response

4. **Multi-skill consideration**: Ask yourself "Would another skill call make this result better?" If yes, call it. Complex tasks typically need 2-4 skill calls.

REMEMBER: The user's original instruction is your NORTH STAR. Every skill call should bring you closer to fulfilling it. Do not give a final response until you can confidently say the user's instruction has been addressed.