# Sentry setup for jonathanperis/* deployable apps

[Sentry](https://sentry.io/) catches runtime errors + perf issues in production. **Free tier: 5K errors/month per project.**

## Apps that benefit (deployable, user-facing)

| Repo | Stack | Sentry SDK |
|------|-------|-----------|
| `jonathanperis.github.io` | Astro / React 19 | `@sentry/astro` |
| `speedy-bird-lynx` | ReactLynx + web build | `@sentry/browser` (web), native module per platform |
| `blazor-mudblazor-starter` | Blazor Server / .NET 9 | `Sentry.AspNetCore` |
| `cpnucleo` | ASP.NET 10 microservices | `Sentry.AspNetCore` per service |
| `super-mango-editor` | C / SDL2 / WASM | optional `@sentry/browser` for the web build |

## One-time setup

1. Sign in to [sentry.io](https://sentry.io/) (use GitHub auth).
2. Create one project per app. Each gets a unique **DSN**.
3. Add the DSN as a GitHub secret named `SENTRY_DSN` (or `SENTRY_DSN_<APP>` if needed) in each repo.
4. (Optional) Generate a Sentry auth token for source-map upload in CI: `SENTRY_AUTH_TOKEN`.

## Per-stack integration

### Astro / React (jonathanperis.github.io)

```bash
bun add @sentry/astro
```

`astro.config.mjs`:
```js
import sentry from "@sentry/astro";
export default {
  integrations: [sentry({
    dsn: process.env.SENTRY_DSN,
    environment: process.env.NODE_ENV,
    sourceMapsUploadOptions: { authToken: process.env.SENTRY_AUTH_TOKEN }
  })]
};
```

### Blazor Server / ASP.NET (cpnucleo, blazor-mudblazor-starter)

`csproj`:
```xml
<PackageReference Include="Sentry.AspNetCore" Version="..." />
```

`Program.cs`:
```csharp
builder.WebHost.UseSentry(o => {
    o.Dsn = builder.Configuration["Sentry:Dsn"];
    o.Environment = builder.Environment.EnvironmentName;
    o.TracesSampleRate = 0.1;
});
```

### ReactLynx (speedy-bird-lynx)

Web build: `@sentry/browser` initialized in `src/index.tsx`.
Native (Android/iOS): native Sentry SDK per platform (out of scope for the JS bundle).

## CI source-map upload (Astro / web example)

Add to the Pages deploy workflow:
```yaml
- name: Upload source maps
  if: env.SENTRY_AUTH_TOKEN != ''
  env:
    SENTRY_AUTH_TOKEN: ${{ secrets.SENTRY_AUTH_TOKEN }}
  run: |
    bunx @sentry/cli releases new "$GITHUB_SHA"
    bunx @sentry/cli releases files "$GITHUB_SHA" upload-sourcemaps ./dist
    bunx @sentry/cli releases finalize "$GITHUB_SHA"
```

## What you get
- Error grouping with stack traces + breadcrumbs
- Release tracking tied to git SHA
- Performance monitoring (transaction traces, web vitals)
- Slack/email/etc. alerting

Pairs with OpenTelemetry already wired into `cpnucleo` — Sentry can ingest OTel traces directly.
