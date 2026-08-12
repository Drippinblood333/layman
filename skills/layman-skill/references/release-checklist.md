# Release Checklist

Use this checklist when the user asks whether a project can ship or how to publish it.

## Blocking Checks

- Build command exists and passes, or the missing command is documented as a blocker.
- Required environment variables are listed with safe example values.
- No secrets, private tokens, credentials, or local-only paths are committed.
- The app can start from documented instructions on a clean machine.
- Core user flow has a manual verification path or automated test.

## Important Non-blocking Checks

- README includes purpose, setup, run, test, build, and deployment notes.
- Error, loading, and empty states are acceptable for the MVP.
- Logs do not expose sensitive data.
- External service failures have a user-visible fallback or clear error.
- Known limitations are documented.

## Deployment Fit

Recommend deployment platform by project type:

- Static frontend: Netlify, Vercel, GitHub Pages, or Cloudflare Pages.
- Full-stack JavaScript app: Vercel, Render, Railway, Fly.io, or a VPS.
- Python API or worker: Render, Railway, Fly.io, or a VPS.
- Internal script or automation: document local execution before hosting.

Do not recommend automatic deployment until build, environment variables, and rollback basics are clear.

## Output Shape

For release checks, produce:

- Blocking items.
- Non-blocking improvements.
- Environment variable status.
- Documentation status.
- Verification commands.
- Recommended deployment target.
- Next safe prompt.

## Safe Next Prompt

```text
请根据刚才的发布前检查，只处理第一个阻塞项。

限制：
1. 只修改与该阻塞项直接相关的文件。
2. 不直接部署。
3. 不新增生产依赖，除非先说明原因并等待确认。
4. 完成后运行可用的验证命令，并总结结果。
```
