# Story 7: Drivers can reserve a space

As a driver, I want to reserve a space in the garage before I arrive, so that I am not turned away when the garage is busy.

## Acceptance criteria

1. A driver can reserve a space when the garage has at least one free space. A reserved space counts as taken: free spaces drop by one.
2. When the garage has no free spaces, the reservation is refused with the reason "garage full", and free spaces stay unchanged.
3. A driver who holds a reservation can cancel it; the space becomes free again.
4. The reservation flow should feel quick.
