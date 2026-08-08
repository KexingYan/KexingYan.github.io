# Crawler Policy

**Effective repository policy:** 2026-07-31
**Applies to:** `https://kexingyan.com/robots.txt`

## Policy objective

The site is intended to be discoverable and citable in ordinary search engines
and AI-assisted search. Model training is a separate use and is not required
for search visibility, citations, or user-requested retrieval. The current
policy therefore:

- allows ordinary search engines;
- allows documented AI search and citation crawlers;
- allows documented user-requested retrieval agents;
- opts out of training crawlers when search and user retrieval are available
  through separate agents;
- allows `Google-Extended` because Google currently combines specified Gemini
  training and grounding uses under that control; and
- allows other standards-compliant crawlers unless a future abuse pattern
  justifies a narrower rule.

This is a crawl preference, not a guarantee of indexing, ranking, retrieval,
citation, or exclusion from every possible dataset.

`robots.txt` is not a privacy, authorization, or security control. Anything
published here must be safe for the public even if a crawler ignores the file
or a user retrieves the URL directly.

## Allowed search and citation crawlers

| User-agent token | Purpose | Policy |
|---|---|---|
| `Googlebot` | Google Search, including eligibility for Google AI search features through the normal Search index | Allow |
| `Bingbot` | Bing Search and search-backed Microsoft experiences | Allow |
| `OAI-SearchBot` | OpenAI search discovery and citation | Allow |
| `ChatGPT-User` | User-triggered OpenAI page retrieval | Allow |
| `Claude-SearchBot` | Anthropic search-result discovery and quality | Allow |
| `Claude-User` | User-triggered Anthropic retrieval | Allow |
| `PerplexityBot` | Perplexity search indexing and result linking | Allow |
| `Perplexity-User` | User-triggered Perplexity retrieval | Allow |

OpenAI states that allowing `OAI-SearchBot` supports inclusion in ChatGPT
search summaries and snippets. Anthropic distinguishes `Claude-SearchBot` and
`Claude-User` from its training crawler. Perplexity states that
`PerplexityBot` is used for search results rather than foundation-model
training.

Official references:

- <https://help.openai.com/en/articles/12627856-publishers-and-developers-faq>
- <https://support.anthropic.com/en/articles/8896518-does-anthropic-crawl-data-from-the-web-and-how-can-site-owners-block-the-crawler>
- <https://docs.perplexity.ai/docs/resources/perplexity-crawlers>
- <https://developers.google.com/search/docs/appearance/ai-features>

## Training and combined-use controls

| User-agent token | Purpose described by operator | Policy |
|---|---|---|
| `GPTBot` | Potential OpenAI model-training collection | Disallow |
| `ClaudeBot` | Potential Anthropic model-training collection | Disallow |
| `Google-Extended` | Control token for specified Gemini training and grounding uses; does not control Google Search | Allow |

OpenAI and Anthropic expose separate search/user agents, so their training
crawlers can be blocked without blocking the documented search paths.
`Google-Extended` is different: Google currently places specified Gemini
training and Gemini grounding under the same control. It is allowed here
because AI retrieval and grounding are explicit site goals. This is a
deliberate trade-off, not a claim that training is required for search.

Allowing `Google-Extended` is therefore not equivalent to allowing Gemini
grounding while fully opting out of training. Normal Google Search and its AI
search features are primarily governed by `Googlebot` and the applicable
Google Search controls. Blocking the named `GPTBot` and `ClaudeBot` tokens also
does not establish that no other training-related access can occur: operators,
agents, datasets, and collection paths can change, and not all access is
covered by these named controls.

The site owner can reverse these choices later. `Google-Extended` is a robots
control token rather than a separate HTTP request user agent. Google documents
that its setting does not affect inclusion or ranking in Google Search.

Official references:

- <https://help.openai.com/en/articles/12627856-publishers-and-developers-faq>
- <https://support.anthropic.com/en/articles/8896518-does-anthropic-crawl-data-from-the-web-and-how-can-site-owners-block-the-crawler>
- <https://developers.google.com/crawling/docs/crawlers-fetchers/google-common-crawlers>

## Ordinary and unknown crawlers

The final wildcard group allows public pages. Search engines not listed
explicitly can therefore crawl the site under their normal rules. The site has
no authenticated, draft, administrative, or private public routes in the
current repository.

Résumé PDFs remain reachable but receive an `X-Robots-Tag: noindex` response
header through `_headers`. They are not disallowed in `robots.txt`, because a
crawler must fetch a resource to observe its HTTP `noindex` directive.

## Cloudflare can override effective access

`robots.txt` is advisory and is only one layer. Cloudflare Pages, WAF, Bot
Fight Mode, managed challenges, rate limits, and custom firewall rules can
still return 403, 429, or a challenge to a crawler that is allowed here.

The following checks must be performed manually in the Cloudflare dashboard:

1. Review **Security → Events** for blocked requests from the allowed crawler
   user agents.
2. Review WAF custom and managed rules for broad bot or country blocks.
3. Review Bot Fight Mode and Super Bot Fight Mode settings.
4. Confirm no rule challenges or blocks verified search-engine bots.
5. For OpenAI, use the current published search crawler IP data where an IP
   rule is necessary: <https://openai.com/searchbot.json>.
6. For Perplexity, use the current official IP files rather than copying a
   static IP list into documentation:
   <https://www.perplexity.com/perplexitybot.json> and
   <https://www.perplexity.com/perplexity-user.json>.
7. Verify that `robots.txt` remains reachable without JavaScript, cookies,
   authentication, or a browser challenge.
8. Confirm the custom-domain redirect keeps every `www` path on the equivalent
   apex path, rather than redirecting all requests to the homepage.

Allow rules based only on a claimed user-agent string are spoofable. Where a
firewall exception is necessary and the operator publishes IP ranges, combine
the official current IP list with the expected user-agent.

## Monitoring and change process

- Review crawler documentation quarterly because bot names and purposes can
  change.
- Review Cloudflare security events after material WAF or bot-management
  changes.
- Run `python3 scripts/validate_site.py` after every robots policy edit.
- Document future additions here before adding them to `robots.txt`.
- Do not add unofficial or guessed user-agent tokens.
- Do not interpret a crawler visit as proof of indexing or citation.
