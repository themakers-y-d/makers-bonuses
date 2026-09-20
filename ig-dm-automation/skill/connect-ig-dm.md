# Connect Instagram comment-to-DM

Owner: the Vibecoder.

Run it when the user wants a word in a comment, or a reply to their story, to send that person a DM with a link. Optionally gated on following first. This is the "reply a word and get the link" automation, running on the user's own Instagram account.

It is a specific case of `connect-a-tool.md`, and it follows that skill's rules. Read that one first if it exists here; this file only adds what is specific to Instagram.

## Before anything

The user needs an Instagram Business or Creator account. A personal account gives no access to comments or messages, and there is no way around it. If theirs is personal, stop and send them to switch it in Instagram settings. It is free and takes a minute.

They also need the kit: the `ig-dm-automation` folder from the MAKERS bonuses repo, with `kit/zernio.mjs` in it.

## How it works

1) Say what is about to happen, in plain words. The system will be able to read comments on their posts and send DMs from their account. It will not be able to post, and it will not be able to see their insights. Name what it will send and to whom, before any technical step.

2) Ask three things, in one wave, not spread across the conversation. Is the account Business or Creator. What word people will reply, and where the link sends them. Whether only followers should get the link.

3) The account and the connection are the user's two clicks, never yours. They sign up at zernio.com, and they approve the Instagram connection. Both grant access to their own account, and an agent does not approve access on someone else's behalf. Tell them exactly what to click and wait.

4) On the Instagram permission screen, tell them to turn two switches off: publish content, and insights. Leave on: profile and media, comments, messages. Least access that does the job.

5) The API key is shown once, right after signup. Tell them that before they sign up, so they copy it when it appears. It goes into `~/.config/ig-dm/zernio.env` as `ZERNIO_API_KEY=sk_...`, chmod 600. Never into the chat, never into a synced folder, never into a repo. A scheduled run is blocked from synced and external drives and fails silently.

6) Prove the connection with one visible read before building anything: `node kit/zernio.mjs doctor`. It must come back with their own Instagram username. Their handle on the screen is proof; "connected" is a claim.

7) Build the rules in `kit/automations.json`, from `automations.example.json`. Keep `platformPostId` as null so the rule covers every post including future ones. Write the copy with the user, not for them, and show it before it goes anywhere. Then `node kit/selfcheck.mjs`, then `node kit/zernio.mjs plan`, and show them the plan. Only then `sync --apply`.

8) Read it back from the server with `node kit/zernio.mjs get <id>`. A field that was silently dropped produces no error, only a lead who gets nothing a month later. The command's own output is not proof.

9) Test it live, and do not finish without it. A comment from the user's own account triggers nothing, by design. Someone else has to comment the word on a real post. Then `node kit/zernio.mjs logs <id>` and show them the row.

10) Record it. One line in `K-knowledge/connected-tools.md`: Instagram comment-to-DM, read comments and send DMs, the date, and that `node kit/zernio.mjs pause <id> --apply` turns it off.

## The one hard rule

Nothing is called done before a real person, from another account, got the message. Everything up to that point proves the configuration is right, not that delivery works, and the two look identical from the inside.

The reason: this automation writes to strangers under the user's name. A broken first message cannot be retried, because Instagram allows exactly one private reply per comment, forever.

## Input and output

In: the user's answers to the three questions, the kit folder, and `K-knowledge/connected-tools.md` if it exists.

Out: live automations proven by a real delivery in the log, the copy saved where the user can edit it, a line in `connected-tools.md`, and the off switch stated out loud.

Before it hands anything back it runs `S-systems/skills/check-before-handback.md`. Anything that went live also runs `ship-it-live.md`.

## The signal you see

Their own Instagram handle coming back from the connection check, before any rule exists. Then, at the end, a real name in the log with the message that went out to them.

## Where it breaks

It breaks when the rule gets pinned to one post, because every later post with the same word then matches nothing and says nothing about it.

It breaks when a keyword is under four characters on partial matching, because Hebrew prefixes glue onto words and a short word becomes a net that catches unrelated comments.

It breaks when the test was done from the owner's own account, which looks exactly like a system that does not work.

And it breaks when another comment-to-DM tool is still running on the same account: the DM is protected by Instagram's one-reply limit, but the public comment reply is not, and two tools will both post under the same person.

## Delete test

Delete this skill and the Vibecoder still connects it, improvising the order each time, and the most common outcome is a setup that reports success and delivers nothing to anyone. The steps that catch that are all here and none of them are obvious.
