# Dennis M. Ritchie: stories

Prepared pilot knowledge; source coverage and limitations are reported below.

- **documented**: Ritchie credited Thompson with most of the early filesystem design and tentatively recalled contributing the device-file idea. Canaday also participated in the early design discussions. ([ritchie-7ca8eec9ac8af9](https://www.nokia.com/bell-labs/about/dennis-m-ritchie/hist.html) / evidence ritchie-7ca8eec9ac8af9-9e97afe4d556)

- **documented**: B's slow threaded code and mismatch with the byte-addressed PDP-11 impeded an OS rewrite. In 1971 Ritchie extended B with a character type and rewrote its compiler to generate machine instructions. ([ritchie-91fa14fdc827e6](https://www.nokia.com/bell-labs/about/dennis-m-ritchie/chist.html) / evidence ritchie-91fa14fdc827e6-386ca4d91206; [ritchie-91fa14fdc827e6](https://www.nokia.com/bell-labs/about/dennis-m-ritchie/chist.html) / evidence ritchie-91fa14fdc827e6-782e6bb24b19)

- **documented**: To make structures workable while preserving much B code, C generated an array's pointer when the array appeared in an expression rather than storing a B-style base pointer. Programs that reassigned array names needed repair. ([ritchie-91fa14fdc827e6](https://www.nokia.com/bell-labs/about/dennis-m-ritchie/chist.html) / evidence ritchie-91fa14fdc827e6-5c5b9dd1158f)

- **documented**: Ritchie contrasted Thompson's unsuccessful first C rewrite attempt with the subsequent rewrite: adding structures made kernel data structures manageable. ([ritchie-56c00e367e631d](https://www.stroustrup.com/From-C-to-Cpp-dmr.pdf) / evidence ritchie-56c00e367e631d-50f223c8244a)

- **documented**: Ritchie and Johnson reported that most of the OS proper retained identical source in the Interdata port after work on declarations and machine-dependent constants. Their account explicitly credits Thompson with the described porting work. ([ritchie-be88b7b72521cb](https://www.nokia.com/bell-labs/about/dennis-m-ritchie/portpap.html) / evidence ritchie-be88b7b72521cb-5627628b41e7)

- **documented**: A recursive-shell example exposed output overwrites caused by process-local file offsets. The solution was a separate system table for open-file I/O pointers. ([ritchie-7ca8eec9ac8af9](https://www.nokia.com/bell-labs/about/dennis-m-ritchie/hist.html) / evidence ritchie-7ca8eec9ac8af9-be7497928907)

- **documented**: For Unicos development, the team chose a less efficient user-mode simulator over more kernel-based work to make development and debugging easier. It was intended for testing, not production, and lacked networking support. ([ritchie-6d2bfd1e17da6d](https://www.nokia.com/bell-labs/about/dennis-m-ritchie/unicos.html) / evidence ritchie-6d2bfd1e17da6d-d7a43f8c2fec; [ritchie-6d2bfd1e17da6d](https://www.nokia.com/bell-labs/about/dennis-m-ritchie/unicos.html) / evidence ritchie-6d2bfd1e17da6d-858daa459e22)

- **documented**: Ritchie implemented a program for Reeds's M-209 attack, crediting Reeds's statistical idea and contributions from both Reeds and Morris. Its reported results were limited to the described English-text tests and assumptions. ([ritchie-a77aa1fa81ba48](https://www.nokia.com/bell-labs/about/dennis-m-ritchie/crypt.html) / evidence ritchie-a77aa1fa81ba48-c478322f0db3; [ritchie-a77aa1fa81ba48](https://www.nokia.com/bell-labs/about/dennis-m-ritchie/crypt.html) / evidence ritchie-a77aa1fa81ba48-6c6614deddad)
