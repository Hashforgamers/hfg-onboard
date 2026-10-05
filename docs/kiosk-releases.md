# Kiosk release management

Apply `sql/20261005_kiosk_releases.sql` to the shared PostgreSQL database before deploying. Deploy hfg-onboard, vendor-Onboard and hash-dashboard together. The super-admin Next.js proxy uses the existing Hash-team login and server-side SUPER_ADMIN_API_KEY.

Super admin → Kiosk releases → enter version, GitHub build reference, release notes and optional installer download → Save draft. Drafts can be edited by version. Active releases are immutable. The supplied Actions artifact link can be saved as a build reference; it cannot be activated as a cafe download.

Publish the installer as a publicly accessible GitHub Release asset (.exe, .msi or .zip). Add its direct github.com/.../releases/download/... link to the draft, then Make active. Activation checks public accessibility before switching the current version; failures leave the old release active. Table locking plus a partial unique index prevents two active versions. An older release can be activated to roll back the download offered to cafes.

The cafe Gaming Consoles page reads `/api/kiosk-release`, which proxies the no-store public metadata endpoint `/api/kiosk/releases/latest`. It displays the active version and download. No active release means the download is unavailable; the old hard-coded Drive link has been removed.

This manages installer distribution. It does not silently install updates on already-linked PCs; the kiosk updater source is not in this workspace. No supplied binary was executed, uploaded or activated during implementation.
