# David Heinemeier Hansson (DHH): principles

Prepared pilot knowledge; source coverage and limitations are reported below.

- **documented**: Programmer happiness is a legitimate design goal, even though it is subjective and difficult to measure. ([dhh-461d2e74ffac9a](https://rubyonrails.org/doctrine) / evidence dhh-461d2e74ffac9a-3321c4866f33)

- **documented**: Powerful language features can cause harm, but prohibiting them also removes useful capabilities. Conventions and education can manage risk; others may reasonably prefer a different trade-off. ([dhh-461d2e74ffac9a](https://rubyonrails.org/doctrine) / evidence dhh-461d2e74ffac9a-bc8f3333bd76)

- **documented**: Extract reusable infrastructure from actual product needs and customer pressure rather than building it speculatively. ([dhh-dac6015dd2ae7f](https://world.hey.com/dhh/five-big-open-source-gifts-from-us-c1b42c1b) / evidence dhh-dac6015dd2ae7f-dc0cce1a1b15)

- **documented**: Evaluate breaking changes against long-term benefits and real migration costs; progress is not permission for needless disruption. ([dhh-461d2e74ffac9a](https://rubyonrails.org/doctrine) / evidence dhh-461d2e74ffac9a-0254397ae243)

- **inferred**: Constraints can force useful prioritization, but ease of implementation must not erase the value a feature needs to deliver. ([dhh-c2552d8a384713](https://37signals.com/podcast/embrace-constraints/) / evidence dhh-c2552d8a384713-ffa56f80804b; [dhh-5f976bac42bd4b](https://37signals.com/podcast/illusions-of-agreement/) / evidence dhh-5f976bac42bd4b-ef1d72bab8d3)

- **documented**: Interpret usage metrics cautiously: a rarely used capability may still be essential to a customer’s decision to buy. The measurement can be correct while the conclusion drawn from it is not. ([dhh-eeeb3124b3987b](https://37signals.com/podcast/focus-on-what-wont-change/) / evidence dhh-eeeb3124b3987b-87598f9bc988)

- **documented**: Long-lived people and software can repay investment through accumulated expertise, but preserving what worked should leave room for a smaller share of experiments. ([dhh-eeeb3124b3987b](https://37signals.com/podcast/focus-on-what-wont-change/) / evidence dhh-eeeb3124b3987b-3f7ca60038d7)

- **documented**: Building quickly for feedback is especially useful where implementation is cheap and feedback arrives quickly; he cautions against transferring the approach unchanged to long-cycle domains. ([dhh-5f976bac42bd4b](https://37signals.com/podcast/illusions-of-agreement/) / evidence dhh-5f976bac42bd4b-bb0f3eaf7433)

- **documented**: Code review can teach in both directions: a less experienced reviewer can surface assumptions or suggest improvements, even when not serving as the senior authority. ([dhh-5f976bac42bd4b](https://37signals.com/podcast/illusions-of-agreement/) / evidence dhh-5f976bac42bd4b-0c139c1aa384)

- **documented**: Treat reliability as requiring redundancy, including geographically separated capacity and replicas of critical infrastructure; his account describes intended design rather than measured availability. ([dhh-47dec4682cb827](https://world.hey.com/dhh/the-big-cloud-exit-faq-20274010) / evidence dhh-47dec4682cb827-d0a4edeb50c8)

- **documented**: After a concentrated migration or launch, stabilize shortcuts and give the team time to recover before another major push. ([dhh-37e8721ebb6b23](https://37signals.com/podcast/leaving-the-cloud-the-finale/) / evidence dhh-37e8721ebb6b23-c14ce8687b38)

- **documented**: In their coauthored work, Fried and Hansson argue that excessive hours can encourage brute-force solutions and impair judgment about which work deserves effort. ([dhh-fec877a93e0c6b](https://37assets.37signals.com/svn/Rework-by-Jason-Fried-and-David-Heinemeier-Hansson-Excerpts.pdf) / evidence dhh-fec877a93e0c6b-6eba23b4aca0; [dhh-fec877a93e0c6b](https://37assets.37signals.com/svn/Rework-by-Jason-Fried-and-David-Heinemeier-Hansson-Excerpts.pdf) / evidence dhh-fec877a93e0c6b-da2495a5a114)
