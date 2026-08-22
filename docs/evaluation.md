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
is 0.0016 with the sign splitting 3/5 and an interval running from -0.004 to
+0.007. That does not make `rasterize_mode` free, which is the same error this
document objects to two paragraphs above: effects as large as either endpoint
are still compatible with five frames. The honest statement is that the
comparison is unresolved, and calling it free needs an equivalence bound set in
advance with the whole interval inside it.

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
looks like the delivery question. Does this exported asset still look like
photographs of this scene? That framing is what motivated the rest of this
section, and it does not survive it.

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
each configuration, rendered at full resolution without loss and scored against
the capture photographs, on two scenes. CMMD uses CLIP ViT-L/14-336 features with a single
bicubic resize to 336 by 336; FID and KID use the standard 2048-d Inception
pool3 features. Uncertainty comes from bootstrap replicates that resample the
frame indices once per replicate and recompute the *difference* under that
shared resampling. The ladder is the opacity pruning threshold at 0, 0.00392,
0.01, 0.02, 0.05 and 0.1.

The first rung is a free calibration check, and not by luck. 0.00392 is 1/255,
which is the cutoff gsplat's rasterizer already applies: `alpha < 1.f / 255.f`
then `continue`, in `rasterize_to_pixels_fwd.cu`. A Gaussian's alpha at a pixel
is its opacity scaled by a factor no greater than one, so a Gaussian whose
opacity sits below that line is skipped at every pixel and contributes to no
image. Pruning at 1/255 cannot change a render, and both scenes duly produce
byte-identical images to the unpruned run. The two configurations are the same
model as far as anything downstream can tell. All three return exactly zero on it with a
zero-width interval, which is what a correctly paired bootstrap has to return on
identical inputs and what independent bootstrapping of the two estimates would
not have returned. KID only does so after the fix described below; on its
standard protocol it returned 0.30.

#### What each one did

The rungs to watch are the fine ones, because the section below measures what
actually separates them: 61 dB on gaudi and 68 dB on r2d2 between the unpruned
render and the 0.01 rung, 53 and 57 dB at 0.02. The images there differ, but
barely. Whether an estimator ought to resolve a difference that small is a
question about how much difference matters, which nothing in this document
settles.

| rung    | gaudi FID | gaudi KID x1000 | gaudi CMMD | r2d2 FID | r2d2 KID x1000 | r2d2 CMMD |
| ------- | --------- | --------------- | ---------- | -------- | -------------- | --------- |
| 0       | 62.68     | 16.553          | 0.4553     | 35.83    | 4.214          | 0.6908    |
| 0.00392 | 62.68     | 16.553          | 0.4553     | 35.83    | 4.214          | 0.6908    |
| 0.01    | 62.65     | 16.515          | 0.4563     | 35.82    | 4.209          | 0.6911    |
| 0.02    | 62.63     | 16.460          | 0.4562     | 35.78    | 4.150          | 0.6984    |
| 0.05    | 63.33     | 16.507          | 0.4696     | 37.29    | 4.649          | 0.7730    |
| 0.1     | 68.10     | 18.200          | 0.5312     | 47.86    | 8.384          | 1.0171    |

All three pass the null rung exactly, returning zero with a zero-width interval
on the pair that renders byte-identical images.

Steps, with an interval excluding zero marked R:

| gaudi step      | ΔFID                    | ΔKID x1000              | ΔCMMD                     |
| --------------- | ----------------------- | ----------------------- | ------------------------- |
| 0 → 0.00392     | +0.000 [+0.000, +0.000] | +0.000 [+0.000, +0.000] | +0.0000 [0.0000, 0.0000]  |
| 0.00392 → 0.01  | -0.036 [-0.082, +0.004] | -0.037 [-0.072, -0.001] R | +0.0009 [-0.0006, +0.0023] |
| 0.01 → 0.02     | -0.011 [-0.131, +0.118] | -0.054 [-0.165, +0.053] | -0.0000 [-0.0018, +0.0019] |
| 0.02 → 0.05     | +0.722 [+0.330, +1.013] R | +0.071 [-0.352, +0.532] | +0.0133 [+0.0095, +0.0178] R |
| 0.05 → 0.1      | +5.514 [+4.150, +6.863] R | +1.842 [+0.906, +2.822] R | +0.0622 [+0.0528, +0.0720] R |

| r2d2 step       | ΔFID                       | ΔKID x1000              | ΔCMMD                       |
| --------------- | -------------------------- | ----------------------- | --------------------------- |
| 0 → 0.00392     | +0.000 [+0.000, +0.000]    | +0.000 [+0.000, +0.000] | +0.0000 [0.0000, 0.0000]    |
| 0.00392 → 0.01  | +0.000 [-0.013, +0.011]    | -0.005 [-0.013, +0.003] | +0.0006 [-0.0007, +0.0019]  |
| 0.01 → 0.02     | -0.052 [-0.138, +0.010]    | -0.059 [-0.104, -0.019] R | +0.0069 [+0.0039, +0.0099] R |
| 0.02 → 0.05     | +1.724 [+1.189, +2.245] R  | +0.522 [+0.170, +0.875] R | +0.0750 [+0.0664, +0.0849] R |
| 0.05 → 0.1      | +11.871 [+10.422, +13.009] R | +3.949 [+2.907, +4.969] R | +0.2477 [+0.2168, +0.2786] R |

The coarse end is unanimous. Every metric resolves 0.05 to 0.1 in both scenes
and all but one resolves 0.02 to 0.05, with intervals nowhere near zero.

The fine end does not sort them out. FID resolves nothing there. CMMD resolves
one step, r2d2 0.01 to 0.02, in the direction of more pruning meaning more
deviation. KID resolves two, gaudi 0.00392 to 0.01 and r2d2 0.01 to 0.02, both
negative, both saying pruning moved the render nearer the photographs.

On r2d2's 0.01 to 0.02 step KID reports -0.059 with an interval of
[-0.104, -0.019] while CMMD reports +0.0069 with [+0.0039, +0.0099]: same
images, same frames, both excluding zero, opposite signs. That is less damning
than it first looks. KID measures a polynomial-kernel distance between Inception
features and CMMD an RBF distance between CLIP features, so a change in the
images can genuinely shorten one and lengthen the other. Nothing is being
contradicted. What it does mean is that at most one of them can be tracking any
single underlying notion of quality, and this data cannot say which, or whether
either does.

An earlier version of this section had FID resolving gaudi's 0.00392 to 0.01
step as an improvement, and I read that as the metric misbehaving. It was the
JPEG encoder, and it vanished when the renders were written losslessly. Worth
recording, because a resolved interval on an artifact is the exact failure this
document is about, produced while writing it.

#### A flaw in the standard KID protocol

KID needed fixing before any of the above could be read. The usual protocol
averages the unbiased MMD over random subsets of the two feature sets, and
drawing those subsets independently for the two configurations under comparison
injects noise that the pairing cannot cancel, because the two runs never see the
same subsets. On the null rung, where the render sets are byte-identical, the
first pass scored 15.76 against 16.07, a difference of 0.30 where the truth is
exactly zero and against a ladder spanning 1.7 end to end. The estimator is
unbiased on the whole set, so the subsetting can be dropped outright. The null
rung then returns exactly zero and the frame bootstrap is the only source of
uncertainty left. Every KID number above is computed that way, and anyone
comparing two configurations with KID should do the same, or at minimum share
the subset draws between them.

#### How much of each is the sample count

Each estimator on the unpruned run, at four frame counts:

| frames | gaudi FID | gaudi KID | gaudi CMMD | frames | r2d2 FID | r2d2 KID | r2d2 CMMD |
| ------ | --------- | --------- | ---------- | ------ | -------- | -------- | --------- |
| 28     | 75.46     | 1.528     | 0.4377     | 36     | 43.44    | -6.431   | 0.6206    |
| 56     | 70.06     | 14.060    | 0.4842     | 73     | 38.58    | 1.164    | 0.6754    |
| 84     | 67.34     | 14.559    | 0.4561     | 110    | 37.60    | 3.887    | 0.7154    |
| 112    | 62.68     | 16.553    | 0.4554     | 147    | 35.83    | 4.214    | 0.6906    |

FID falls monotonically as frames are added in both scenes, which is the bias
Chong and Forsyth describe. The drift is 12.8 points on gaudi against a ladder
whose whole range is 5.4, so the number cannot be read on its own and two
configurations evaluated at different frame counts cannot be compared at all.
The steps above survive because the shared bootstrap cancels the part of that
bias the two runs have in common.

KID is worse in a different way. A single draw at 36 frames puts the r2d2 run at
-6.4, a negative squared distance, which an unbiased estimator is entitled to
produce and which supports no ordering whatsoever. Unbiased in expectation is
not the same as usable from one draw at this size. CMMD wanders least in
relative terms but still moves more between 28 and 56 frames than the entire
0.02 to 0.05 step it is being asked to detect.

Three limits apply to all of the above. These are training views, which the
model was fit to, so they understate every degradation. The reference set is our
own capture frames, tourists included, so a model that correctly drops a
transient is penalised for it. And an interval spanning zero means the test
could not resolve that step at this sample size, which is not the same as the
step being free.

#### What to take from this

No opinion scores exist for this ladder, and nothing here supplies a substitute.
The fine rungs render 53 to 68 dB apart, which says the images barely differ, and
it is tempting to read a resolved interval there as a false positive. That
reading does not hold. The images do differ, so an estimator separating them is
detecting something real; a narrow interval around a tiny effect is what
sensitivity looks like. Calling it an error would need an equivalence bound
declared in advance and an interval that fits inside it, which is the same thing
this document demands before anyone calls PSNR blind. No such bound exists here.

So the fine end ranks nobody. FID resolves nothing, CMMD resolves one step, KID
resolves two, and which behaviour is correct depends on a threshold nobody has
set.

What does separate them needs no labels, because it is about the estimators
rather than the images. Two things, and the first version of one of them was
wrong.

FID's absolute level falls 12.8 points between 28 and 112 frames, more than
twice the range of the whole ladder, so it cannot be read as a number and two
configurations scored at different frame counts cannot be compared at all. The
paired steps survive because the shared bootstrap cancels the part of that drift
the two runs have in common. Nothing rescues the level.

The second is discriminability under matched samples. Each metric's own
bootstrap supplies its sampling deviation, on the same frames under the same
resampling, so the ratio of a step to that deviation compares estimators in
spite of their different units. On the four steps where the renders genuinely
differ:

| step             | FID   | KID  | CMMD  |
| ---------------- | ----- | ---- | ----- |
| gaudi 0.02→0.05  | 4.15  | 0.31 | 6.32  |
| gaudi 0.05→0.1   | 7.97  | 3.77 | 12.70 |
| r2d2 0.02→0.05   | 6.40  | 2.90 | 15.90 |
| r2d2 0.05→0.1    | 17.98 | 7.50 | 15.72 |

CMMD leads in three of the four and KID trails in all four, while FID takes the
largest step on r2d2. That is the comparison this conclusion needed. An earlier
version rested it on KID returning -6.4 at 36 frames, which does not support
anything: a negative value is exactly what an unbiased U-statistic is entitled
to produce, it bars reading that point estimate as an absolute distance, and it
leaves untouched the paired differences the tables above are built from. CMMD's
estimator is the biased V-statistic and nonnegative by construction, so never
going negative is a property of its formula rather than evidence of stability.

The fine steps are left out of that table on purpose. A higher ratio there would
mean only that an estimator separates images that barely differ, and whether
that is a virtue is the question no bound has settled.

All three resolve the coarse rungs cleanly and agree on direction there, which
is the regime where the choice of metric stops mattering.

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
had: an answer that is checkable against a fact rather than against another
metric.

## Scoring against the export instead of the photographs

The section above ends by arguing that the pre-transform export is the better
reference for anything applied after training. That is cheap to test, since the
renders already exist. Each rung scored against the unpruned render at the same
poses, per frame, LPIPS with a 95% interval on the mean:

| threshold | gaudi LPIPS vs unpruned      | PSNR dB | r2d2 LPIPS vs unpruned       | PSNR dB |
| --------- | ---------------------------- | ------- | ---------------------------- | ------- |
| 0         | 0.00000 [0.00000, 0.00000]   | inf     | 0.00000 [0.00000, 0.00000]   | inf     |
| 0.00392   | 0.00000 [0.00000, 0.00000]   | inf     | 0.00000 [0.00000, 0.00000]   | inf     |
| 0.01      | 0.00005 [0.00005, 0.00005]   | 61.02   | 0.00002 [0.00002, 0.00002]   | 68.01   |
| 0.02      | 0.00030 [0.00029, 0.00031]   | 53.41   | 0.00031 [0.00030, 0.00032]   | 57.02   |
| 0.05      | 0.00322 [0.00313, 0.00331]   | 43.20   | 0.00775 [0.00756, 0.00793]   | 42.14   |
| 0.1       | 0.02032 [0.01979, 0.02084]   | 34.01   | 0.05406 [0.05291, 0.05520]   | 31.59   |

These are lossless renders. The first attempt used the q95 JPEGs the render
script writes by default and produced 0.00085 and 0.00038 at the 0.01 rung,
seventeen and nineteen times the truth. Encoding the same checkpoint twice and
comparing the copies puts the encoder's own error at 0.00795 LPIPS and 48.5 dB,
which is nothing against a photograph, since renders sit around 22 dB from
those, and overwhelming against another render at 61 to 68 dB. The artifacts
mostly cancel between two nearly identical images and decorrelate as the images
separate, so the contamination grows with the rung instead of sitting under
everything as a constant floor: seventeen times at 0.01, six at 0.02, and still
1.7 at 0.05. Write PNG for any render-against-render comparison.

Every problem the distribution metrics had disappears. The ladder is monotone in
both scenes. No neighbouring pair of intervals overlaps. The identity rung
returns exactly zero with infinite PSNR, which is a fact rather than a
calibration hope. Where FID, KID and CMMD each inverted somewhere and left the
fine rungs unresolved, this separates all five rungs in both scenes, and the
intervals are narrow enough that the separation is not close.

The reason is not that LPIPS is a better metric than CMMD. It is that the
comparison is paired at the level of individual frames against an exact
reference, so nothing has to be estimated from a sample of 112 images. The
question changed, and the easier question has a much better answer.

What it buys is a real decision. Both scenes start from a 1M cap. Pruning at
0.05 leaves 628k Gaussians on gaudi and 619k on r2d2, a cut of roughly 38% in
both, and moves the delivered image by 0.0032 and 0.0078 LPIPS at 42 to 43 dB.
Pruning at 0.1 leaves 446k and 324k, cuts of 55% and 68%, and moves it by 0.020
and 0.054 at around 32 dB.

The fine rungs come out very small indeed: 61 dB on gaudi and 68 dB on r2d2 at
0.01. That says nothing about the threshold actually being shipped. The step
from 0.01 to 0.05 is where almost all of the deviation and almost all of the
size saving happen, and 0.0032 and 0.0078 LPIPS at 42 dB is a magnitude, not a
verdict. What this replaces is the previous state of affairs, where the number
was unmeasured and the threshold was set by assertion. Whether it is small
enough to ship is still the study's question, now asked about a known
quantity.

Two things it still cannot do. The unpruned export wins by construction, so this
can never report that pruning improved anything, only how far it moved. And a
0.0032 LPIPS deviation is not a statement about what a viewer would notice,
which remains the open question the study below is meant to close.

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
