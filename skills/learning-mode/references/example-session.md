# Example session (shortened)

The learner is a new engineer. The change adds a retry to a sync client. Goal: be ready to explain it in review.

**Assistant:** Goal first: you want to explain this change in review. What parts feel solid, and which feel fuzzy?

**Learner:** The retry loop is fuzzy. I mostly accepted what the AI wrote.

**Assistant:** That is a useful thing to say. Let us start there. The loop retries up to 5 times. Before we run it: what do you expect to happen if the server returns 500 three times and then 200?

**Learner:** It tries 3 times, fails, and gives up?

**Assistant:** Close, and the interesting part is "gives up". Look at line 12: what does the loop do after a failed attempt?

**Learner:** Oh, it sleeps and tries again. So it succeeds on the fourth try.

**Assistant:** Yes: you read the sleep-and-retry correctly. Now check it yourself rather than taking my word. Run the test `test_retry_then_succeeds`. What do you predict?

**Learner:** It passes, with four calls to the server.

**Assistant:** Run it. (The learner runs it: it passes, four calls.) Your prediction held. Next: this retries on every error. What would go wrong if the call were "charge the card"?

**Learner:** I am not sure.

**Assistant:** Hint: think about a request that worked on the server but whose response got lost.

**Learner:** It would charge twice!

**Assistant:** That is the key risk, and you found it. So what does the retry need to be safe? (The learner proposes an idempotency key.) Good. Last step: write two sentences in your own words for the PR: what the retry does, and the risk you checked.

**Learner:** (writes the note in the template; the assistant does not rewrite it, and only asks one question about a vague phrase.)

**Assistant:** Anything you are still unsure about? Put it in the "still unsure" line. That is honest, and it is what a reviewer wants to see.

Things this session did on purpose: asked for a prediction first, verified by running, gave a hint instead of the answer, praised one specific correct thing, let the learner write the note, and ended with what remains unclear.
