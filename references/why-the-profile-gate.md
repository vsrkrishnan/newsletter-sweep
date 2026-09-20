# Why `applies_to_me.md` is a hard requirement

Every general-purpose "summarize my newsletters" tool already exists, and
none of them are worth using twice. The reason is the same in every case:
a neutral summary of an article tells you what the article says, which you
could get by reading the article's own summary. It doesn't tell you
anything you didn't already have.

The one thing that makes triage worth automating is a restatement **from
your own seat**: not "this piece covers agentic coding patterns" but "this
specifically means you should reconsider how you're scoping the eval step
in what you're building." That's a judgment call the tool can only make if
it knows who you are and what you're trying to do.

So `newsletter-sweep run` refuses to proceed without a profile — not as a
paternalistic gate, but because running it without one produces the exact
commodity output this tool exists to replace, and shipping that as a
"working" default would be worse than refusing.

## Why this is cheap, not a chore

The obvious objection: requiring a written profile before first use adds
friction to the five-minute path. The fix isn't to drop the requirement —
it's to make writing it fast. `newsletter-sweep init` asks two short
questions (what do you do, what are you trying to get better at), drafts a
profile from the answers, and lets you edit it. Most people spend under a
minute here. See `examples/security-aware-pm/applies_to_me.md` for what a
filled-in one actually looks like.

## What "good" looks like

A profile doesn't need to be long. It needs to be specific enough that two
different readers with the same profile would actually make similar
judgment calls about what's worth their time. "I'm interested in AI" is
not specific. "I'm a product manager with a security background trying to
get sharper on agentic AI failure modes, and I'm not interested in generic
'AI is changing everything' framing" is.
