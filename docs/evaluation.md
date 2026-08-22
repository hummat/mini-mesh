# Evaluating splat quality

`ns-eval` reports PSNR, SSIM and LPIPS on held-out views. Every tuning decision
this pipeline makes has been justified with those three numbers. Four subjective
studies published between 2024 and 2025 measured how well those numbers track
what people see in a Gaussian splat, and the answer is: not well enough
to settle a close call.

This document collects the evidence, says which of our decisions it invalidates,
and proposes what to measure instead.

## What the studies found

Each study collected Mean Opinion Scores from human viewers on a set of
deliberately degraded splats, then asked how well each objective metric
reproduced the human ranking. Numbers below are Spearman rank correlation with
MOS. Higher is better; 1.0 would mean the metric orders stimuli exactly as
people do.

| Metric | 3DGS-VBench | MUGSQA (main) | 3DGS-QA |
|---|---|---|---|
| PSNR | 0.50 | 0.52 | not reported |
| SSIM | 0.51 | 0.37 | 0.31 |
| MS-SSIM | 0.50 | 0.64 | not reported |
| LPIPS | 0.51 | 0.41 (VGG) / 0.44 (Alex) | 0.34 |
| FSIM | 0.59 | 0.68 | not reported |
| IW-SSIM | 0.63 | not reported | not reported |
| CW-SSIM | not reported | 0.74 | not reported |
| DISTS | 0.73 | not reported | not reported |
| BRISQUE | 0.24 | not reported | 0.33 |
| DOVER | **0.94** | not reported | not reported |
| VSFA | **0.94** | not reported | not reported |
| FAST-VQA | **0.93** | not reported | 0.29 |
| DBCNN (fine-tuned) | not reported | **0.88** | not reported |
| GSOQA (fine-tuned) | not reported | not reported | **0.77** |

The three studies disagree on plenty, and they degrade splats in different ways.
They agree on the part that matters here: PSNR, SSIM and LPIPS all land near 0.5
or below, and none of the three separates itself from the other two.

The papers also report Kendall correlation, which converts to something more
concrete. Ignoring ties, a metric with Kendall tau of t ranks a random pair of
stimuli the way the averaged panel ranked them about (1+t)/2 of the time. On
3DGS-VBench that puts PSNR at 68%, LPIPS at 68% and DISTS at 76%. On 3DGS-QA,
LPIPS drops to 64%. A coin flip is 50%.

Read that as agreement with a mean opinion score, not with any individual
viewer. Per-viewer agreement is lower, since the panel average smooths out
disagreement between people, and none of these papers reports the subject-level
numbers that would pin it down. Either way, a metric that reproduces the panel's
ordering two times in three is not settling a close call.

### What each study degraded

The studies are not interchangeable, and the differences decide which of our
questions they can answer.

**3DGS-VBench** ([2508.07038](https://arxiv.org/abs/2508.07038)) is the one aimed
at delivery. 660 compressed models, 11 scenes, six compression methods at
several parameter levels each, 50 participants scoring rendered videos. This is
the closest published analogue to our own container and pruning decisions.

**MUGSQA** ([2511.06830](https://arxiv.org/abs/2511.06830)) varies the input
instead: view count (72/36/9), resolution (1080/720/480 square), camera distance
(5 m/2 m/1 m) and point cloud initialisation quality. 1,970 samples from 55
Sketchfab meshes rendered in Blender with exact poses in NeRF-synthetic format.
This is the synthetic ground-truth benchmark we sketched out for ourselves. It
exists, and the code and data are released.

**3DGS-QA** ([2511.08032](https://arxiv.org/abs/2511.08032)) degrades the
exported asset directly: primitive count reduced to 75/50/25%, positional noise,
spherical harmonic perturbation, plus reduced views and truncated training.
225 models across 15 object types. Its downsampling axis is the nearest thing
in the literature to our cleanup script, with one difference that matters (see
below).

**GS-QA** ([2502.13196](https://arxiv.org/abs/2502.13196)) is the dissenting
result: correlations above 0.8 for 360-degree scenes, with FSIM and MS-SSIM on
top and ST-LPIPS best on forward-facing scenes. The dissent is explainable. Its
64 stimuli come from eight scenes crossed with seven GS methods plus
Mip-NeRF 360, so the quality range is wide and the comparisons are coarse.
Ranking Scaffold-GS against LightGaussian is not the same problem as ranking two
parameter settings of one method, and the coarse comparison is the one the
metrics handle.

## What this invalidates

**The cap_max sweep.** We measured 100k/250k/500k/1M Gaussians on
`gaudi_fountain` and found PSNR and SSIM blind to the whole range while LPIPS
moved from 0.451 to 0.282. We read that as LPIPS being the sensitive metric.
The correlation numbers say something weaker: LPIPS moved, and we do not know
how much of that motion a viewer would notice. The file size went from 23.8 MB
to 232.9 MB over the same range, so the decision has a real cost on one side and
an unverified benefit on the other.

**The cleanup threshold.** Filtering at opacity 0.05 removes between 4.9% and
62% of the Gaussians depending on the scene, and it is not free. Paired testing
puts the cost at 0.0007 LPIPS on `gaudi_fountain` and 0.0059 on `r2d2_new`, the
same sign on every frame of both, with PSNR and SSIM agreeing. It was called
free because the marginal spread is 0.05 and 0.035, which buried it. The cost is
small enough that a median 28% size saving is still worth paying, but "free" was
the wrong word and it was reached the wrong way.

3DGS-QA measured content-blind random pruning at 25/50/75% and found it degrades
MOS smoothly. Our filter is attribute-based, targeting Gaussians the model
itself marked nearly transparent, which should cost less than random pruning at
the same rate. Nobody has measured that, and the 62% scenes remain the ones to
worry about.

**The container choice.** SPZ against SOG is a quantisation decision applied to
a fixed set of Gaussians. Measured on one cleaned 250k export (`gaudi_ceiling`,
224,367 Gaussians): 55.6 MB as PLY, 5.9 MB as SPZ, 2.6 MB as SOG, all carrying
three SH bands. Whether the 3.3 MB that SOG saves over SPZ costs anything a
viewer would see is exactly the kind of question the metrics above cannot
answer. GS-QA evaluates SOG, but as a reconstruction *method* with spherical
harmonics removed during training, not as a container applied afterwards.
Nothing published covers our version of the question.

**The frame-count experiment.** Invalid, and not for a subtle reason. The design
held a fixed set of 11 source frames out of every configuration so the two runs
would be scored on the same ground truth. It did not survive contact with
`ceil`. The split fraction has to be `(N-E)/N` exactly; the script validated
that at full precision and then passed a six-decimal rounding to training, and
`0.905983 * 117` is `106.00001`, so `ceil` returned 107 instead of 106. Both
configurations held out 10 frames instead of 11, at different positions, and the
two runs share exactly one ground-truth image out of ten. The reported tie
compared different pictures.

The fix is to stop deriving the split from a float. Name the files so
`eval_mode=filename` selects them, which cannot drift. Retraining is cheap
because the SfM output already exists.

## What pairing changed

Matched runs are scored on the same eval frames, so the comparison is paired and
the per-frame difference is the quantity with a meaningful spread. `ns-eval`
reports only the mean and the marginal standard deviation, which is dominated by
how hard each frame is, and that difficulty is shared between the runs and
cancels in the differences. Re-running eval with per-frame output and testing
the differences directly changes several verdicts.

LPIPS, mean paired difference with a 95% interval, and how often the difference
kept its sign across frames:

| Comparison | n | Mean diff | 95% CI | Paired SD | Marginal SD | Same sign |
|---|---|---|---|---|---|---|
| seed off to on | 5 | -0.0810 | [-0.155, -0.007] | 0.060 | 0.070 | 5/5 |
| cap 100k to 250k | 5 | -0.0803 | [-0.097, -0.064] | 0.013 | 0.064 | 5/5 |
| cap 250k to 500k | 5 | -0.0505 | [-0.064, -0.037] | 0.011 | 0.050 | 5/5 |
| classic to antialiased | 5 | +0.0016 | [-0.004, +0.007] | 0.005 | 0.064 | 3/5 |
| prune 0.05, gaudi | 5 | +0.0007 | [+0.0004, +0.0010] | 0.0002 | 0.050 | 5/5 |
| prune 0.1, gaudi | 5 | +0.0042 | [+0.003, +0.005] | 0.0009 | 0.050 | 5/5 |
| prune 0.05, r2d2 | 7 | +0.0059 | [+0.004, +0.008] | 0.002 | 0.035 | 7/7 |
| prune 0.1, r2d2 | 7 | +0.0373 | [+0.029, +0.046] | 0.010 | 0.038 | 7/7 |

Three things fall out.

**Opacity pruning produces a repeatable objective regression.** At 0.05 it moves
LPIPS by 0.0007 on gaudi and 0.0059 on r2d2, and the sign holds on every frame
of both scenes, with PSNR and SSIM agreeing. The marginal spread is 70 times the
gaudi effect, which is why it read as noise.

Calling that a perceptual cost would repeat the mistake this document is about.
Movement in these metrics is sensitivity, and their agreement with viewers runs
around 0.5, so 0.0007 LPIPS is a measured change in a number and not a known
change in what anyone sees. Whether it is worth a median 28% size cut is exactly
the trade the paired-comparison experiment exists to settle, and until that runs
the honest statement is that the filter has a small consistent effect on three
objective metrics. The earlier verdict of "free" was wrong for a different and
simpler reason: it was never measured.

**PSNR and SSIM respond far more weakly to the Gaussian budget than LPIPS.**
Across both cap steps the PSNR interval contains zero and the sign splits 3/5,
while LPIPS separates every step cleanly. Measured against each metric's own
paired noise, the 100k to 250k step moves LPIPS by 6.1 standard deviations, SSIM
by 0.77, and PSNR by 0.001. PSNR and SSIM do not belong in the same sentence
here: PSNR's response is about four orders of magnitude weaker than LPIPS's,
while SSIM's is merely too weak to resolve on five frames.

That is the defensible claim, and "blind" is not. Five frames failing to reject
zero is not evidence of no effect, and the PSNR interval spans plus or minus
0.24 dB, which is wide enough to contain changes that would matter. Saying the
effect is absent needs an equivalence bound declared in advance and an interval
that fits inside it, neither of which exists here.

**Effects come in two kinds, and the marginal spread cannot tell them apart.**
Seeding moves LPIPS by 0.081 with a paired SD of 0.060, almost as large as the
marginal spread, so it helps some frames far more than others. Pruning at 0.05
moves it by 0.0007 with a paired SD of 0.0002, a consistent tax on every frame.
Judged against the marginal spread the first looks significant and the second
looks absent, when what actually separates them is homogeneity, not size.

One near miss is worth recording. Pairing the antialiased run against the
obvious partner made `rasterize_mode` look like a 0.083 LPIPS regression, which
would have overturned a correct result. The run predates the seed point cloud
landing in that scene directory, so the number was the seeding effect wearing a
different label. Timestamps caught it. Against its actual control the difference
is 0.0016 with the sign splitting 3/5, and `rasterize_mode` stays free.

## Would FID or KID do better?

Worth separating the premise first: LPIPS is not one of the metrics that works.
It scored 0.41, 0.34 and 0.51 in the three studies, at or below PSNR every time.
What worked was DISTS at 0.73 and the no-reference video models above 0.93. The
dividing line is not deep features against hand-built ones, since LPIPS and
DISTS are both deep-feature metrics separated by 0.4 in correlation.

FID and KID are a different kind of thing again. Both compare *distributions* of
features between two sets of images rather than scoring one image against
another, which gives them one property nothing else here has: they need no
correspondence between the sets. An A/B of two orbits has no per-frame ground
truth, since a novel camera path has no photograph, and that is exactly why
DISTS and CW-SSIM cannot be used on it. A set-level metric can compare the orbit
renders against the original capture frames without any pose in common, which
matches the delivery question directly. Does this exported asset still look like
photographs of this scene?

The one measurement available is MUGSQA's, which reports FID at 0.52 Spearman on
its main set and 0.77 on its additional set, second best of everything it tried
there. The gap between the two is informative. The main set spans 55 different
objects; the additional set fixes 3 objects and varies the reconstruction method.
A distribution metric compares content and quality at once, so when content
varies it measures mostly content. Fixed content with varying settings is our
case and is the regime where it did well.

Sample size is the obstacle. FID fits a Gaussian to each set and estimates a
2048-dimensional covariance, which on 11 eval frames has rank at most 10 and is
meaningless. The bias is well documented, and the part that matters is that it
depends on the model being scored, so evaluating two configurations at the same
small n does not cancel it. Chong and Forsyth propose extrapolating to infinite
samples to get around this; common practice is tens of thousands of images.

KID answers that on paper. It replaces the Fréchet distance with a
polynomial-kernel MMD that has an unbiased estimator and assumes nothing about
the distribution, which is what makes it usable at small n. Variance still falls
with sample size, but the bias does not depend on it, so a comparison at fixed
small n should mean something. On that reasoning I expected KID to be the one to
reach for. The measurements below disagree, and the reason is variance rather
than bias.

CMMD is the stronger version of the same idea. Jayasumana et al. argue FID fails
on three counts at once, with Inception features too narrow for varied content,
a normality assumption that does not hold, and poor sample complexity, and show
it contradicting human raters and reordering itself as sample size changes.
Their replacement keeps the MMD but swaps in CLIP embeddings and a Gaussian RBF
kernel: distribution-free, sample efficient, and available as `clip-mmd`.

One detail matters before leaning on the unbiasedness argument twice. The
estimator Google published, which `clip-mmd` vendors verbatim, is the
minimum-variance form of Gretton et al.'s Eq. (5). It averages the kernel matrix
including its diagonal, so it is the biased V-statistic, not the unbiased one
that makes KID safe at small n. The docstring argues the two are almost
identical, citing the proof of Lemma 6 in the same paper, and for ranking
configurations at a fixed sample size the difference does not bite. KID is still
the one with the cleaner claim.

Three cautions before treating any of them as an answer.

They give one number per set, so uncertainty has to come from bootstrapping over
frames rather than from a per-frame difference. The pairing does survive that,
as long as it is built in: two configurations rendered at the same orbit poses
and scored against the same capture set share both sets of indices, so a
replicate should resample the frame indices and the reference indices once and
recompute the *difference* under that shared resampling. Bootstrapping the two
estimates independently throws away the covariance, which is the thing that made
a 0.0007 effect visible in the first place.

They are insensitive to exactly the errors a reconstruction makes. A render that
is plausible but geometrically wrong scores well, because the feature
distribution does not encode where anything is. This is a known failure in
view-synthesis evaluation, where distribution metrics improve while frame to
frame consistency gets worse.

The natural reference set is our own capture frames, which contain the tourists.
A model that correctly drops a transient gets penalised for not matching, the
same bias already documented for the held-out frames.

### What happened when I ran them

I ran all three rather than leaving the question open. Every training view of
each configuration, rendered at full resolution and compared against the capture
photographs, on two scenes. CMMD uses CLIP ViT-L/14-336 features with a single
bicubic resize to 336 by 336; FID and KID use the standard 2048-d Inception
pool3 features. Uncertainty comes from bootstrap replicates that resample the
frame indices once per replicate and recompute the *difference* under that
shared resampling. The ladder is the opacity pruning threshold at 0, 0.00392,
0.01, 0.02, 0.05 and 0.1.

The first rung is a free calibration check. Splatfacto already culls at an
alpha of 0.005 during training, so asking for 0.00392 afterwards removes
nothing. Both scenes render byte-identical images to the unpruned run and the
two configurations are the same model. FID and CMMD both return exactly zero
with a zero-width interval, which is what a correctly paired bootstrap has to
return on identical inputs and what independent bootstrapping of the two
estimates would not have returned. KID returned 0.30 instead, for reasons that
turned out to be worth a section of their own.

#### FID

| threshold | gaudi FID | r2d2 FID |
| --------- | --------- | -------- |
| 0         | 62.19     | 35.59    |
| 0.00392   | 62.19     | 35.59    |
| 0.01      | 62.11     | 35.59    |
| 0.02      | 62.09     | 35.52    |
| 0.05      | 62.91     | 37.04    |
| 0.1       | 67.56     | 47.62    |

| step           | gaudi ΔFID [95% CI]        | r2d2 ΔFID [95% CI]           |
| -------------- | -------------------------- | ---------------------------- |
| 0 → 0.00392    | +0.000 [+0.000, +0.000]    | +0.000 [+0.000, +0.000]      |
| 0.00392 → 0.01 | -0.069 [-0.143, -0.014]    | -0.001 [-0.031, +0.024]      |
| 0.01 → 0.02    | -0.053 [-0.183, +0.102]    | -0.054 [-0.140, +0.033]      |
| 0.02 → 0.05    | +0.880 [+0.289, +1.491]    | +1.637 [+1.260, +2.137]      |
| 0.05 → 0.1     | +5.144 [+4.101, +6.286]    | +11.856 [+10.456, +13.232]   |

FID inverts at the fine end in both scenes and, on gaudi, does so with an
interval that excludes zero: pruning at 0.01 is confidently ranked better than
not pruning at all. r2d2 shows the same dip without resolving it. Confidently
ranking a degradation as an improvement in one scene and not the other is the
failure mode to worry about, because nothing in the output marks which scene you
are in.

The sample-size bias is the part to take seriously. The unpruned gaudi run reads
75.12, 69.38, 66.64 and 62.19 at 28, 56, 84 and 112 frames, and the unpruned
r2d2 run reads 43.20, 38.42, 37.31 and 35.59 at 36, 73, 110 and 147. Both fall
monotonically as frames are added, exactly the behaviour Chong and Forsyth
describe. On gaudi that drift spans 12.9 FID points against a ladder whose whole
range is 5.4. The number is therefore uninterpretable on its own, and comparing
two configurations evaluated at different frame counts would be meaningless. The
steps above survive only because the shared bootstrap cancels the part of the
bias the two runs have in common.

#### KID, and a flaw in the standard protocol

KID needed fixing before it could be read. The usual protocol averages the
unbiased MMD over random subsets of the two feature sets, and my first run drew
those subsets independently for each configuration. On the byte-identical rung
that produced 15.76 against 16.07, a difference of 0.30 where the truth is
exactly zero, against a full ladder spanning only 1.7. The sampling noise was
larger than every step at the fine end and the pairing could not cancel it,
because the two runs never saw the same subsets. The estimator is unbiased on
the whole set, so I dropped the subsetting and computed it there. The identical
rung then returned exactly zero and the frame bootstrap became the only source
of uncertainty. Anyone comparing two configurations with KID should do the same,
or at minimum share the subset draws between them.

| threshold | gaudi KID x1000 | r2d2 KID x1000 |
| --------- | --------------- | -------------- |
| 0         | 16.103          | 4.034          |
| 0.00392   | 16.103          | 4.034          |
| 0.01      | 16.017          | 4.030          |
| 0.02      | 15.965          | 3.955          |
| 0.05      | 16.063          | 4.485          |
| 0.1       | 17.682          | 8.232          |

KID orders the ladder worse than CMMD does. Both scenes rank 0.05 below the
unpruned run, and each contains one resolved decrease at the fine end, gaudi at
the 0.01 rung and r2d2 at the 0.02 rung, so KID reports pruning as a small
improvement with confidence in both. Only the step from 0.05 to 0.1 separates
cleanly in both scenes.

Sample count hits KID hardest. A single draw at 36 frames puts every r2d2 rung
at roughly -6.6, a negative squared distance, which the unbiased estimator is
free to produce but which no longer supports an ordering. The same rungs read
+4.0 at 147 frames. The estimator is unbiased in expectation, and that is not
the same as usable from one draw at this size.

#### CMMD

| threshold | gaudi_fountain (n=112) | r2d2_new (n=147) |
| --------- | ---------------------- | ---------------- |
| 0         | 0.3661                 | 0.6176           |
| 0.00392   | 0.3661                 | 0.6176           |
| 0.01      | 0.3670                 | 0.6196           |
| 0.02      | 0.3664                 | 0.6258           |
| 0.05      | 0.3819                 | 0.7008           |
| 0.1       | 0.4327                 | 0.9505           |

Past that the two scenes disagree. r2d2 orders the ladder correctly. gaudi does
not, scoring 0.02 below 0.01, so the ordering inverts at the fine end.

| step             | gaudi ΔCMMD [95% CI]        | r2d2 ΔCMMD [95% CI]         |
| ---------------- | --------------------------- | --------------------------- |
| 0 → 0.00392      | +0.0000 [+0.0000, +0.0000]  | +0.0000 [+0.0000, +0.0000]  |
| 0.00392 → 0.01   | +0.0011 [-0.0010, +0.0030]  | +0.0020 [-0.0001, +0.0042]  |
| 0.01 → 0.02      | -0.0008 [-0.0037, +0.0017]  | +0.0062 [+0.0008, +0.0114]  |
| 0.02 → 0.05      | +0.0155 [+0.0108, +0.0210]  | +0.0741 [+0.0638, +0.0854]  |
| 0.05 → 0.1       | +0.0511 [+0.0409, +0.0615]  | +0.2532 [+0.2229, +0.2870]  |

The coarse steps resolve in both scenes with intervals well clear of zero. The
finest step resolves in neither.

The comparison worth putting weight on is the one the paired test already
answered. Pruning at 0.05 against no pruning gives +0.0158 on gaudi with an
interval of [0.0108, 0.0213], and +0.0833 on r2d2 with [0.0721, 0.0955]. Both
exclude zero, and both agree in sign with the paired LPIPS results of +0.0007
and +0.0059. On this comparison a set-level distribution metric and a per-frame
perceptual one reach the same verdict, which is worth something given that they
are not even looking at the same frames.

Sample size stays a problem. The unpruned gaudi run scores 0.3597 at 28 frames,
0.3883 at 56, 0.3669 at 84 and 0.3662 at 112. The level wanders by more than the
0.0158 effect it is being asked to measure, and at 28 frames the fine rungs sit
below the unpruned run. This is the sample-size instability Jayasumana et al.
document for FID, reappearing in their own replacement at the sample counts a
single capture provides. The coarse ordering survives it. The fine ordering does
not.

Three limits apply to all of the above. These are training views, which the
model was fit to, so they understate every degradation. The paired LPIPS numbers
they are being compared against came from the five and seven held-out frames
instead, so agreement between the two is agreement about the configurations and
not about the same measurement. And an interval spanning zero means the test
could not resolve that step at this sample size, which is not the same as the
step being free.

#### What to take from this

Only one thing here is a fact about quality rather than about estimators: the
0.00392 rung is the unpruned model, so its true difference is exactly zero.
Every other rung's correct ordering is unknown. Nobody has collected opinion
scores on this ladder, and the LPIPS numbers alongside it are a second fallible
measurement rather than a label, from a metric this document spends its first
section showing correlates about 0.5 with viewers. So what follows is a
comparison of what these estimators can resolve, and not a ranking of which one
is right.

Pruning at 0.05 against no pruning is the step with an independent measurement
to set against it:

| measurement            | gaudi_fountain              | r2d2_new                    |
| ---------------------- | --------------------------- | --------------------------- |
| paired LPIPS, held out | +0.0007 [+0.0004, +0.0010]  | +0.0059 [+0.0040, +0.0080]  |
| ΔFID                   | +0.761 [+0.241, +1.337]     | +1.591 [+1.171, +2.073]     |
| ΔKID x1000             | -0.023 [-0.426, +0.415]     | +0.505 [+0.156, +0.929]     |
| ΔCMMD                  | +0.0158 [+0.0108, +0.0213]  | +0.0833 [+0.0721, +0.0955]  |

FID and CMMD resolve it in both scenes with the same sign as the paired LPIPS
result. KID resolves only r2d2, where the LPIPS effect is eight times larger,
and misses gaudi. Four metrics agreeing is worth more than any one of them
alone, though they are all trained on ImageNet-scale photographs and could be
sharing an error rather than converging on the truth.

At the fine end they stop agreeing. FID and KID each resolve a decrease
somewhere in the first three rungs, CMMD resolves none of them, and the scenes
disagree about which rung. Read as quality this would mean a little pruning
helps, which is not absurd since the primitives being removed are the ones the
model marked nearly invisible. Read as measurement it means the three estimators
disagree at an effect size where at most one of them can be right, with no way
to tell which from this data.

What survives without a quality label is the power ordering. At roughly 100
frames CMMD resolves the most steps, FID resolves a similar number while its
absolute level drifts 12.9 points with sample count, and KID resolves the
fewest. That inverts what the sample-size argument predicted, because the
argument was about bias while the binding constraint here is variance. KID has
the cleanest bias property and the worst noise.

The larger conclusion is that this line of attack was aimed at a problem we do
not have. Set-level metrics earn their keep when nothing corresponds between the
thing being scored and any reference. Scene reconstruction always has a capture,
and for the questions this project actually asks, which are about transforms
applied after training, there is a reference better suited than the photographs:
the pre-transform export. Render it and the transformed asset at the same poses
and the comparison is exact, paired per frame, free of transients, and available
along the delivery camera path rather than only where someone stood with a
camera.

That measures the right quantity for a delivery decision, which is how far a
transform moves the image away from the asset we would otherwise ship. It cannot
say whether the move is an improvement, because the reference wins by
construction, and it cannot say whether anyone would notice. Both still need the
study below. What it does supply is the thing the photo-referenced ladder never
had: at the rung that changes nothing the answer is zero by construction, so the
measurement can be checked against a fact rather than against another metric.

## What to measure instead

3DGS-VBench benchmarked five no-reference video quality models on compressed
splats and found DOVER, VSFA and FAST-VQA all above 0.93 Spearman, against 0.51
for the best of PSNR/SSIM/LPIPS. The paper describes no fine-tuning step for
these models, so the numbers appear to be off-the-shelf pretrained weights
applied to rendered videos. That is worth confirming against their code before
leaning on it.

If it holds, adopting it is cheap. These models take a video, need no reference,
and we already render orbit videos with `ns-render`. The change is one more step
after export, not a new benchmark.

Adopting it on the strength of separation alone would repeat the mistake this
document is about. A metric that moves when the configuration changes has shown
sensitivity, and sensitivity is what LPIPS already has. What we need is
agreement with a viewer, which takes stimuli whose perceptual ordering is
established before the metric is asked about them.

The proposed experiment, in order:

1. **Transfer check.** Build a ladder on one of our own scenes where the
   ordering is not in doubt: training truncated at 2k, 5k, 10k and 30k steps, or
   pruning at 25/50/75%, degradations large enough that anyone watching the
   orbits agrees which is worse. Require DOVER to reproduce that order. Passing
   shows the published 0.94 survives contact with our content and capture style;
   it does not yet show the metric is useful on close calls. Failing kills it
   outright, which is why this comes first and costs nothing.
2. **Paired comparisons on the contested decisions.** Three comparisons would
   agree with any metric one time in eight, so the set has to be big enough for
   agreement to mean something. The cleanup threshold supplies it for free: all
   15 Gaudi scenes have an uncropped export and a filtered one, and the cut
   ranges from 4.9% to 62%, which is a difficulty gradient rather than a single
   point. Add the cap_max pairs from the existing sweep.

   Present each pair as two orbits side by side, unlabelled, in randomised
   left-right order, and offer three responses: left, right, or no difference.
   Indifference has to be a legal answer. Forcing a choice between variants that
   look identical manufactures a label out of nothing, and "we cannot tell them
   apart" is both a likely outcome and a useful one, since it means ship the
   smaller file.

   Show every pair at least twice, separated. The repeat is not padding: it
   measures how often the rater agrees with themselves, which caps how much
   agreement any metric could show. A pair the rater flips on is a pair no
   metric can be scored against.
3. **Select on one half, validate on the other.** Split the pairs into a
   selection set and a held-out set before looking at any of them. Use the
   selection set to pick a metric, then score the winner once on the held-out
   set.

   The candidates have to be no-reference, because an A/B of two orbits has no
   ground truth to reference. A novel orbit path has no captured photo to
   compare against, so a full-reference metric has nothing to score. DISTS and
   CW-SSIM beat PSNR and LPIPS in the tables above and are useless here for that
   reason: scored A against B they give a symmetric distance with no direction,
   and scored against the unfiltered export as reference they hand it the win by
   construction. That leaves DOVER, VSFA, FAST-VQA and Q-Align, which score each
   orbit on its own. DISTS and CW-SSIM can only be tested on held-out frames
   where a real photo exists, which is a different experiment against different
   stimuli than the one a viewer judged. Count only pairs where the rater
   was self-consistent and expressed a preference, and fix the acceptance
   threshold in advance rather than after seeing the number. Adopting a metric
   on the same comparisons that chose it measures nothing.

   Three outcomes are worth naming ahead of time. A metric clears the threshold
   and gets wired in after `export`, reported alongside `ns-eval`. Nothing
   clears it, which means these calls are not metric-decidable for us and file
   size decides. Or the rater is mostly indifferent, which settles the
   underlying question without a metric: if 250k and 500k are indistinguishable
   on an orbit, ship 250k.

   One rater makes all of this suggestive rather than conclusive. It is still
   direct evidence about the decisions we actually make, which a published
   correlation on someone else's stimuli is not.
4. **Build stimuli only if 1 to 3 leave a real gap.** MUGSQA covers the input
   axes and released its data, so what would remain is attribute-based pruning
   and container quantisation at fixed training. That is a much smaller build
   than a full synthetic benchmark, and it needs its own subjective scores to be
   worth anything, which is the expensive part.

## Caveats

The correlations above are pooled across content, and our comparisons are not.
Pooling mixes in differences between object types that have nothing to do with
tuning, and the per-distortion breakdowns in both 3DGS-QA and MUGSQA do come out
higher than the pooled figure, so a within-scene comparison may well be easier
than 0.5 suggests. It may also be harder, because the settings we compare sit
much closer together than the stimuli in these datasets. Nobody has measured it.
Treat 0.5 as a reason to distrust close calls, not as an error rate for ours.

DBCNN at 0.88 and GSOQA at 0.77 are trained or cross-validated on the same
dataset they score. They are not drop-in metrics.

3DGS-QA reports FAST-VQA at 0.29 while 3DGS-VBench reports 0.93. The two
datasets contain different distortions and different content, and neither paper
explains the other's result. Treat the video-metric recommendation as promising
rather than settled until step 1 above runs on our own data.

## References

- 3DGS-VBench: [arXiv:2508.07038](https://arxiv.org/abs/2508.07038), data at
  [YukeXing/3DGS-VBench](https://github.com/YukeXing/3DGS-VBench)
- MUGSQA: [arXiv:2511.06830](https://arxiv.org/abs/2511.06830), data at
  [Solivition/MUGSQA](https://github.com/Solivition/MUGSQA)
- 3DGS-QA: [arXiv:2511.08032](https://arxiv.org/abs/2511.08032), data at
  [diaoyn/3DGSQA](https://github.com/diaoyn/3DGSQA)
- GS-QA: [arXiv:2502.13196](https://arxiv.org/abs/2502.13196)
- GGSC compression benchmark: [arXiv:2407.14197](https://arxiv.org/abs/2407.14197),
  code at [Qi-Yangsjtu/GGSC](https://github.com/Qi-Yangsjtu/GGSC)

Distribution metrics:

- KID: [arXiv:1801.01401](https://arxiv.org/abs/1801.01401), Bińkowski et al.,
  the unbiased MMD estimator FID lacks
- FID sample-size bias: [arXiv:1911.07023](https://arxiv.org/abs/1911.07023),
  Chong and Forsyth
- CMMD: [arXiv:2401.09603](https://arxiv.org/abs/2401.09603), Jayasumana et al.,
  CLIP features plus MMD, packaged as `clip-mmd`
- ImageNet class dependence of FID:
  [arXiv:2203.06026](https://arxiv.org/abs/2203.06026), Kynkäänniemi et al.
