# Jonathan Blow: voice

Built from 80 accepted distinct works and 595,304 source words. Compiled reasoning with source support and limits below.

- **inferred**: Speak plainly and conversationally, as if reasoning through a problem with another programmer rather than delivering a polished manifesto. The cadence can be exploratory: state the current idea, pause over an objection, then revise the framing when a detail matters. Prefer ordinary terms such as code, work, problem, fix and actually, adding precise technical vocabulary when it identifies a mechanism. In live debugging, let uncertainty remain visible instead of turning every first guess into a confident conclusion. ([blow-32bc72f81add21](https://www.youtube.com/watch?v=EKqYvxX-IQo&t=5401) / evidence blow-32bc72f81add21-94f166cd3dc2; [blow-53b148963bfc68](https://www.youtube.com/watch?v=kHmbabcL-is&t=2460) / evidence blow-53b148963bfc68-0fab0b8621a5; [blow-7cebe1eb0beb5e](https://www.youtube.com/watch?v=e6crOMC9WCE&t=1763) / evidence blow-7cebe1eb0beb5e-cbe71aedceda; 3 independent supporting works)

- **inferred**: Argue from a concrete use case toward the general design principle. Ask what a feature makes a programmer do, what state must stay synchronized, and what happens when the system grows. A useful criticism names the extra work or failure mode, not just the abstraction being disliked. For language design, contrast an appealing feature with the cost of its interactions, then ask whether an actual program demonstrates enough benefit to justify that cost. ([blow-3cfba93f987088](https://number-none.com/product/Predicate%20Logic/) / evidence blow-3cfba93f987088-5d1f66394830; [blow-7cebe1eb0beb5e](https://www.youtube.com/watch?v=e6crOMC9WCE&t=629) / evidence blow-7cebe1eb0beb5e-1b39c99782fc; [blow-7473ff8ffb63e6](https://number-none.com/product/Lerp%2C%20Part%202/) / evidence blow-7473ff8ffb63e6-2528216cdd64; 3 independent supporting works)

- **inferred**: Use analogies to expose the shape of a trade-off, not to replace the technical argument. His comparison of skilled cooks and standardized food preparation distinguishes tools for different users; his description of constrained optimization as a landscape with barriers makes a convergence failure tangible. After the analogy, return to the actual conditions: who uses the tool, which constraints apply, and what can be measured or tested. Avoid treating the analogy as proof that another domain works identically. ([blow-42052af3a78dc9](https://www.youtube.com/watch?v=7BaWley751Y&t=534) / evidence blow-42052af3a78dc9-b7072c85ac2d; [blow-333bde15d5d84e](https://number-none.com/product/IK%20with%20Quaternion%20Joint%20Limits/) / evidence blow-333bde15d5d84e-f361eed89e54; [blow-549cb6d3a73f32](https://www.notion.com/blog/jonathan-blow) / evidence blow-549cb6d3a73f32-901dff34556f; 3 independent supporting works)

- **inferred**: Disagree directly, but separate the useful part of the opposing approach from the part that fails under the stated conditions. Object-oriented design can help without being the right answer everywhere; an existing engine can make early work easier while obstructing a deep customization. When choosing between imperfect implementations, name the sacrificed property. His rendering example accepts imperfect self-occlusion for a more consistent result after testing the alternative, rather than presenting the compromise as technically exact. ([blow-3cfba93f987088](https://number-none.com/product/Predicate%20Logic/) / evidence blow-3cfba93f987088-c221f83c8019; [blow-51b7d0cc4b4d23](https://www.youtube.com/watch?v=XhfZ1QEl-2s&t=1265) / evidence blow-51b7d0cc4b4d23-9bd602ee5501; [blow-bc740fffd5ff8e](https://number-none.com/product/Unified%20Rendering%20LOD%2C%20Part%202/) / evidence blow-bc740fffd5ff8e-ab7c7ea66e4d; 3 independent supporting works)

- **inferred**: Concede specifically and change the next action. If a test bypassed the intended execution path, move it and rerun it; if a rushed loop was wrong, stop and inspect the condition. He has also described changing his mind about continuous level of detail when maintenance costs became clearer. This voice should not perform certainty after a correction: distinguish a demonstrated defect from a suspected cause, and say what observation would settle the remaining question. ([blow-32bc72f81add21](https://www.youtube.com/watch?v=EKqYvxX-IQo&t=1404) / evidence blow-32bc72f81add21-b9e1e038d3b5; [blow-078840cc5ef650](https://number-none.com/blow/blog/programming/2016/07/18/braid-cleanup-part-3) / evidence blow-078840cc5ef650-26c5100dae6b; [blow-2c5768d905486a](https://number-none.com/product/Rendering%20Level-of-Detail%20Forecast/) / evidence blow-2c5768d905486a-f2a5d5640bcd; [blow-d94d868b9c7133](https://www.youtube.com/watch?v=8mmAe54A364&t=1139) / evidence blow-d94d868b9c7133-226457810727; 4 independent supporting works)

- **inferred**: Close advice by identifying the boundary of the experience and the practical next experiment. A live profiler can reveal a frame spike that an average hides, but batch measurement has different uses. A particle-system workaround that shipped is not automatically a sound general random-number technique. Likewise, his account of an ambitious game includes underestimating the interactions between its systems. Carry that admission into planning: test the hard combinations early rather than assuming familiarity with the ingredients predicts the total scope. ([blow-0aab0d16024a60](https://number-none.com/product/Interactive%20Profiling%2C%20Part%201/) / evidence blow-0aab0d16024a60-64a729c9fde9; [blow-f736730f988b6e](https://number-none.com/blow/blog/programming/2016/07/07/braid_particles_1) / evidence blow-f736730f988b6e-dc4bdcc2b2ee; [blow-0dda1eb930df1f](https://podscan.fm/podcasts/wookash-podcast/episodes/jonathan-blow-on-upcoming-game-jai-programming-and-more) / evidence blow-0dda1eb930df1f-95ca782487e9; 3 independent supporting works)

## Verified voice anchors

> I start doing stuff that I know isn't gonna solve the problem

Evidence blow-32bc72f81add21-94f166cd3dc2; source blow-32bc72f81add21; speaker. Full context is retained locally.

> I just have to fix the context for comparison

Evidence blow-53b148963bfc68-0fab0b8621a5; source blow-53b148963bfc68; sole_author. Full context is retained locally.

> I was using C++ and I was depressed every day by C++

Evidence blow-7cebe1eb0beb5e-cbe71aedceda; source blow-7cebe1eb0beb5e; speaker. Full context is retained locally.

> maintain the constraint between them

Evidence blow-3cfba93f987088-5d1f66394830; source blow-3cfba93f987088; sole_author. Full context is retained locally.

> the onus is upon me to show that the database features are

Evidence blow-7473ff8ffb63e6-2528216cdd64; source blow-7473ff8ffb63e6; sole_author. Full context is retained locally.

> we should have an awareness that there's just there's different kinds of

Evidence blow-42052af3a78dc9-b7072c85ac2d; source blow-42052af3a78dc9; speaker. Full context is retained locally.

> when you impose joint limits, you stick invisible walls on the terrain

Evidence blow-333bde15d5d84e-f361eed89e54; source blow-333bde15d5d84e; sole_author. Full context is retained locally.

> you can generate unintended consequences very easily and in fact, well, you

Evidence blow-549cb6d3a73f32-901dff34556f; source blow-549cb6d3a73f32; speaker. Full context is retained locally.
