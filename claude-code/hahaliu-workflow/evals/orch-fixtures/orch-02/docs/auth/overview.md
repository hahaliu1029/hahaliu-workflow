# Auth module

Access tokens are JWTs with a 15-minute TTL; refresh tokens rotate on every use
and are stored server-side. Risk: refresh rotation has no replay detection, so a
stolen refresh token races the legitimate client until first reuse is noticed.
