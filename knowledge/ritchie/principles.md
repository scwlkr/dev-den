# Dennis M. Ritchie: principles

Prepared pilot knowledge; source coverage and limitations are reported below.

- **documented**: Use the system being designed: Ritchie and Thompson argued that direct use exposes deficiencies and motivates correction; accessible, modifiable source supported revision. ([ritchie-4495b38593615b](https://www.nokia.com/bell-labs/about/dennis-m-ritchie/cacm.html) / evidence ritchie-4495b38593615b-6f6b67dafcaa)

- **documented**: Leave file-content structure to programs when the system interface can usefully treat files as byte streams. This does not prevent programs from agreeing on structured formats. ([ritchie-f9fdc2ceaea02e](https://www.nokia.com/bell-labs/about/dennis-m-ritchie/notes.html) / evidence ritchie-f9fdc2ceaea02e-f1b56987b0aa; [ritchie-4495b38593615b](https://www.nokia.com/bell-labs/about/dennis-m-ritchie/cacm.html) / evidence ritchie-4495b38593615b-0db7c2c23d73)

- **documented**: Separate checks from code generation when that preserves the ability to build existing programs. Ritchie and Johnson described lint as a separate checker partly because outlawing every suspect construct was infeasible. ([ritchie-be88b7b72521cb](https://www.nokia.com/bell-labs/about/dennis-m-ritchie/portpap.html) / evidence ritchie-be88b7b72521cb-2032cd3e9b85)

- **documented**: Encapsulate volatile representations: Ritchie and Johnson described standard translation routines as protection against changes over time, not merely differences between machines. ([ritchie-be88b7b72521cb](https://www.nokia.com/bell-labs/about/dennis-m-ritchie/portpap.html) / evidence ritchie-be88b7b72521cb-9a4169267e3b)

- **documented**: Consider implementation during language design. Ritchie noted that apparently elegant or orthogonal features can reveal unexpected consequences and difficulty when compilers are built. ([ritchie-983276307fabd9](https://www.nokia.com/bell-labs/about/dennis-m-ritchie/hopl.html) / evidence ritchie-983276307fabd9-2a9dc72025d0)

- **documented**: For calling conventions, Ritchie and Johnson advised maintaining valid environment registers at interruptible points and having a stack-unwinding algorithm before committing to a frame design. ([ritchie-5d25d1308143eb](https://www.nokia.com/bell-labs/about/dennis-m-ritchie/clcs.html) / evidence ritchie-5d25d1308143eb-96d903e24349; [ritchie-5d25d1308143eb](https://www.nokia.com/bell-labs/about/dennis-m-ritchie/clcs.html) / evidence ritchie-5d25d1308143eb-50370e959c65)

- **documented**: Language usefulness depends on understandable definitions, available implementations, and interaction with a real environment—not just the ability to express algorithms. ([ritchie-983276307fabd9](https://www.nokia.com/bell-labs/about/dennis-m-ritchie/hopl.html) / evidence ritchie-983276307fabd9-0adfa051a12e; [ritchie-983276307fabd9](https://www.nokia.com/bell-labs/about/dennis-m-ritchie/hopl.html) / evidence ritchie-983276307fabd9-07da9dc80445)
