# Question bank

Pick one question that fits the learner's level and the part of the change that matters. Levels: **L1** says what it does, **L2** says why and what if, **L3** transfers the idea to a new situation. Move up only when the learner answers comfortably.

## Predict (before running)
- What will this print or return for input X? (L1)
- Which line runs first, and what is the value of `y` there? (L1)
- If I change the input to the empty case, what happens? (L2)

## Trace
- Walk through this function with one real input, line by line. (L1)
- Where does this value come from, and who else can change it? (L2)

## Purpose and design
- What problem does this part solve, in one sentence? (L1)
- Why this approach and not B? What did B cost? (L2)
- Which acceptance criterion does this code exist to satisfy? (L2)

## Break it
- What fails first if I delete this line? Why? (L2)
- What input would make this wrong? (L2)
- What happens under two requests at once? (L3)

## Change it
- The requirement changes to Y. Which parts change and which do not? (L3)
- How would you make this twice as fast, and what would you give up? (L3)

## Test it
- Which test would catch it if this regressed? Does one exist? (L2)
- How would you prove the test can fail? (L2, see red-to-green in `verify-and-evals`)

## Evaluate the AI
- What did the AI assume that nobody told it? Which assumption would you check first? (L2)
- Which name here (function, flag, package, config key) could have been invented? How do you check? (L2)
- What would you not trust in this change without running it? (L3)

## Security and operations
- Who can reach this, and what stops the wrong person? (L2)
- What would you look at in production to know it is misbehaving? (L3)

## What a good answer contains
A claim, the reason for it, and a way to check it. A fluent answer with no way to check is a prompt for "how would you verify that?", not a pass.
