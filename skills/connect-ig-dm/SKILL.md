---
name: connect-ig-dm
description: Sets up the automation where someone replies a keyword on a reel, a post or a story and gets a DM with the link seconds later, optionally only once they follow. Use this whenever the owner says "תגיבו מילה ותקבלו", "אני רוצה מאני צ'אט", "תחבר לי DM אוטומטי באינסטגרם", "אוטומציית תגובות", "מישהו מגיב ומקבל לינק", "set up comment to DM", "replace ManyChat", or asks for a word in a comment to send someone a link. Always use this instead of connect-a-tool on its own. That skill covers connecting any account in general, while this one carries the Instagram rules that decide between a system that delivers and one that reports success and delivers nothing.
---

# Connect Instagram comment-to-DM

Owner: the Vibecoder.

⚠️ This sends messages to real strangers under the owner's name. Follow the steps in order. Where a step says stop, stop.

This is a specific case of `connect-a-tool`. Everything in that skill applies. What follows is only what Instagram adds.

## Before anything, one check that can end it

The owner needs an Instagram **Business or Creator** account. A personal account gives no access to comments or messages, and there is no way around it.

If theirs is personal, stop and send them to switch it in Instagram settings. It is free and takes a minute. Do not continue until they confirm.

They also need the kit: the `ig-dm-automation` folder from the MAKERS bonuses repo, with `kit/zernio.mjs` in it.

## Steps

1) **Say what is about to happen, before anything technical.** The system will read comments on their posts and send DMs from their account. It will not post on their behalf and it will not see their insights. Name what it will send, and to whom.

2) **Ask three things in one wave**, not spread across the conversation. Is the account Business or Creator. What word people will reply, and where the link sends them. Whether only followers should get the link.

3) **Two clicks are theirs, never yours.** They sign up at zernio.com, and they approve the Instagram connection. Both grant access to their own account, and an agent does not approve access on someone else's behalf. Tell them exactly what to click, then wait.

4) **On the Instagram permission screen, two switches go off**: publish content, and insights. Leave on: profile and media, comments, messages. Least access that does the job.

5) **The API key shows once**, right after signup. Tell them that *before* they sign up so they copy it when it appears. It goes to `~/.config/ig-dm/zernio.env` as `ZERNIO_API_KEY=sk_...`, chmod 600.

   Never into the chat, never into a repo, and never into iCloud, Dropbox or an external drive. A scheduled run is blocked from synced drives and fails silently, which looks exactly like a bug in the code.

6) **Prove the connection with one visible read before building anything.** Run `node kit/zernio.mjs doctor`. It must come back with their own Instagram handle. Their handle on the screen is proof. The word "connected" is a claim.

7) **Build the rules** in `kit/automations.json`, starting from `automations.example.json`.

   Keep `platformPostId` as `null`. That makes the rule cover every post, including the ones they have not published yet. A rule pinned to one post stops covering the next one and says nothing about it.

   Keep keywords at four characters or more on partial matching. Hebrew prefixes glue onto words, so a short word becomes a net that catches unrelated comments.

   Write the copy **with** the owner, not for them, and show it before it goes anywhere. This is the text strangers will read in their name.

8) **Dry run, then show, then apply.** `node kit/selfcheck.mjs`, then `node kit/zernio.mjs plan`, and put the plan in front of them. Only then `sync --apply`.

9) **Read it back from the server.** `node kit/zernio.mjs get <id>`. Confirm the follow gate, the buttons and the variations are actually there. A field that was silently dropped raises no error. It produces one lead who gets nothing, a month later.

10) **Test it live, and do not finish without it.** A comment from the owner's own account triggers nothing, by design. Someone else has to comment the word on a real post. Then `node kit/zernio.mjs logs <id>` and show them the row.

    Until that row exists, the configuration is right and delivery is unproven. Those two look identical from the inside.

11) **Record it.** `tools.md` already exists at the root of their system with a table and the rules around it. Add **one row**: Instagram comment-to-DM, access read and write, the date, and `node kit/zernio.mjs pause <id> --apply` as the off switch. ⛔ Never rewrite that file. The sections around the table are what tell them how to switch things off.

12) **Save the asset.** The keywords and the copy go to `3-work/now/ig-dm/` with a dated name, and the owner is told where it is. Run `/ship-it-live`, because this touched a live account and sent messages to real people. Run `/final-pass` before handing anything back. Anything learned goes to the Archivist as a proposed line, never written directly.

## The one hard rule

Nothing is called done before a real person, from another account, received the message.

The reason is not caution. Instagram allows exactly one private reply per comment, forever. A first message that went out broken cannot be retried to that person.

## The signal the owner sees

Their own Instagram handle coming back from the connection check, before any rule exists. Then a real name in the log, with the message that went out to them.

## Where it breaks

It breaks when the rule is pinned to one post, because every later post with the same word matches nothing and reports nothing.

It breaks when the test was done from the owner's own account, which looks exactly like a system that does not work.

It breaks when another comment-to-DM tool still runs on the same account. The DM is protected by Instagram's one-reply limit, but the public comment reply is not, and both tools will post under the same person.

And it breaks when a keyword is short on partial matching, which quietly turns a magnet into a spam complaint.
