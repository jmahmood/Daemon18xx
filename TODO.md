# Deferred work

These are deliberately outside the current API/discovery/deployment work.

- **1830 automatic best-route calculation — decision deferred.** Players choose
  routes; the backend validates them and computes revenue. An automatic optimum
  search is a separate, complex feature and is not required for play. Retain the
  existing manual route workflow. No new solver is planned in the current scope.
- **Responsiveness and performance optimization — deferred.** Measure concurrent
  requests and expensive route searches before considering worker processes or
  background jobs. Do not introduce those architectural changes in the current
  scope. Snapshot/history growth and database indexing can be assessed with
  actual usage measurements.
