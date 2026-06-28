# TensorBoard Training Analysis & Hyperparameter Tuning Plan

This document analyzes the training metrics from the live TensorBoard logs (run `MaskablePPO_1` up to 2,000,896 steps) and outlines concrete improvements to the reinforcement learning training pipeline.

---

## 1. Deep-Dive Analysis of TensorBoard Metrics

### 1.1 Policy Entropy Loss (`train/entropy_loss`)
* **Observation**: The entropy loss starts near `-0.9` and rapidly rises (moving toward zero randomness) to `-0.33` by 1.0M steps, where it plateaus.
* **Diagnosis**: **Early Entropy Collapse**. With 73 actions, the raw random entropy should be higher. However, action masking zero-outs invalid choices (restricting options to the request's secondary area, typically leaving only 8 to 21 active stations). This smaller active action space, combined with a default entropy coefficient of `ent_coef=0.0`, causes the policy to become highly deterministic too quickly.
* **Impact**: The agent stops exploring alternative station assignments early in training, getting trapped in local optima. This is why the reward plateaus and fails to surpass the weighted baseline.

### 1.2 Approximate KL Divergence (`train/approx_kl`)
* **Observation**: The approximate KL divergence starts low but climbs to **`0.05` to `0.07`** after 600k steps, remaining high with large variance.
* **Diagnosis**: **Unstable Policy Updates**. For standard PPO, a KL divergence above `0.02` is considered dangerously high. High KL indicates that policy updates are too large, which overrides previously learned optimal routing policies, leading to training instability and sub-optimal convergence.
* **Impact**: Destructive policy updates prevent the agent from fine-tuning its decisions to achieve zero violations (causing it to suffer 1 voltage violation in evaluation, compared to 0 for the weighted baseline).

### 1.3 Explained Variance (`train/explained_variance`)
* **Observation**: Rises to `0.68` and plateaus.
* **Diagnosis**: The value function is moderately accurate (predicting 68% of the return variance), but there is room for improvement. Stable environments with accurate value heads usually show explained variance above `0.80`. Squeezing the 2200-dimensional input vector into a small value network limits its ability to accurately assess the stress impact of specific station nodes.

### 1.4 Reward Mean (`rollout/ep_rew_mean`)
* **Observation**: Steep improvement from step 0 to 400k, followed by a complete plateau between `-3.8` and `-4.2`.
* **Diagnosis**: **Premature Convergence**. Because of entropy collapse and high KL steps, the policy reaches a plateau early (around 600k steps) and fails to continue learning.

### 1.5 System Throughput (`time/fps`)
* **Observation**: Stepwise drop from 21 FPS down to 17 FPS.
* **Diagnosis**: **Performance Degradation**. Since we are running in `recorded` replay mode, FPS should remain flat. A declining FPS indicates cumulative memory leaks or CPU overhead (e.g. growing arrays or lists inside the custom scenario cycler or callbacks).

---

## 2. Diagnosed Root Causes

1. **Severe Representation Bottleneck**: The observation space is **2200-dimensional** (10 global features + 73 stations $\times$ 30 features). Stable-Baselines3's default MLP policy architecture utilizes a network of `[64, 64]` for the actor (`pi`) and critic (`vf`). Squeezing a 2200-dim vector into a 64-unit bottleneck destroys spatial context and makes learning fine-grained grid interactions extremely difficult.
2. **Lack of Exploration Pressure**: `ent_coef` is set to `0.0`. There is no incentive for the agent to try slightly higher-stress stations that might offer better charging speeds or less travel time, leading to early convergence to the first safe-looking station.
3. **Large Optimization Step Sizes**: The default learning rate of `3e-4` with `10` epochs per rollout causes the policy to shift too far in a single update step, triggering the high KL divergence (`~0.06`).

---

## 3. Recommended Hyperparameter Tuning Plan

To solve these bottlenecks, we will modify the hyperparameters during **Stage A** training:

| Parameter | Default (Live Run) | Proposed Tuning | Target Improvement |
| :--- | :---: | :---: | :--- |
| **Network Architecture** | `[64, 64]` | `pi=[512, 256]`, `vf=[512, 256]` | Increase network capacity to parse 2200 features |
| **Entropy Coefficient (`ent_coef`)**| `0.0` | `0.01` (or decaying schedule) | Maintain exploration, prevent early entropy collapse |
| **Learning Rate** | `3e-4` | `1e-4` or `8e-5` | Stabilize updates, lower KL divergence |
| **Target KL Limit (`target_kl`)** | `None` | `0.015` | Terminate training epochs early if policy drifts too far |
| **Optimization Epochs (`n_epochs`)**| `10` | `4` or `5` | Reduce updates per rollout to prevent overfitting |
| **Batch Size** | `64` | `128` or `256` | Smoother gradient estimates over scenario cycles |
| **Rollout Steps (`n_steps`)** | `2048` | `4096` | More samples per gradient update |

---

## 4. Implementation Details for Code Modifications

We can modify `train_maskable_ppo_feeder_station_selector.py` to expose these hyperparameters as command-line arguments. This allows us to run tuned experiments.

### Proposed Code Changes in `train_maskable_ppo_feeder_station_selector.py`

#### 4.1 CLI Argument Additions
Add options to `parse_args()`:
```python
    parser.add_argument("--learning-rate", type=float, default=3e-4, help="Learning rate for PPO optimizer")
    parser.add_argument("--ent-coef", type=float, default=0.0, help="Entropy coefficient for exploration")
    parser.add_argument("--n-epochs", type=int, default=10, help="Number of epochs per optimization cycle")
    parser.add_argument("--n-steps", type=int, default=2048, help="Number of rollout steps per env step")
    parser.add_argument("--batch-size", type=int, default=64, help="Minibatch size for optimization")
    parser.add_argument("--target-kl", type=float, default=None, help="Target KL divergence to stop updates early")
    parser.add_argument("--net-arch", default="64,64", help="Comma-separated architecture for policy and value layers")
```

#### 4.2 Applying Config to Model Construction
Construct policy networks and hyperparameters:
```python
    # Parse net_arch string (e.g. "512,256")
    layers = [int(x) for x in args.net_arch.split(",") if x.strip()]
    policy_kwargs = dict(
        net_arch=dict(pi=layers, vf=layers)
    )

    model = MaskablePPO(
        "MlpPolicy",
        env,
        learning_rate=args.learning_rate,
        n_steps=args.n_steps,
        batch_size=args.batch_size,
        n_epochs=args.n_epochs,
        ent_coef=args.ent_coef,
        target_kl=args.target_kl,
        policy_kwargs=policy_kwargs,
        verbose=1,
        seed=scenarios[0].seed,
        tensorboard_log=str(args.tensorboard_log),
    )
```

---

## 5. Next Steps
1. **Apply the code changes** to `train_maskable_ppo_feeder_station_selector.py` to expose the hyperparameters.
2. **Launch a tuned training run** using the new CLI configuration:
   ```powershell
   python scripts\rl_training\train_maskable_ppo_feeder_station_selector.py `
     --feeder-rl-data-dir A:\coding\Projects\USSEE\Implementations\DigitalTwin.2.0\outputs\evside_feeder_rl `
     --output-dir models\rl_feeder_tuned `
     --tensorboard-log outputs\rl_feeder\tensorboard_tuned `
     --grid-advisory-mode recorded `
     --grid-evaluation-mode replay `
     --scenario-count 512 `
     --duration-hours 24 `
     --total-timesteps 2000000 `
     --learning-rate 1e-4 `
     --ent-coef 0.01 `
     --target-kl 0.015 `
     --n-epochs 5 `
     --n-steps 4096 `
     --batch-size 128 `
     --net-arch 512,256
   ```
3. **Verify training improvement** by checking that `train/entropy_loss` decays slowly, `train/approx_kl` stabilizes below `0.02`, and `rollout/ep_rew_mean` climbs above `-3.8` to match or exceed the weighted greedy baseline.
