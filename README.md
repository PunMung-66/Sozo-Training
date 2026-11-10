# Sozo Slurm Pipeline

Use Ansible from your local computer to prepare one or more KMUTT Slurm accounts, update project code, download DVC data, and submit a job.

## 1. Install Ansible

On Ubuntu or Debian:

```bash
sudo apt update
sudo apt install ansible
ansible --version
```

## 2. Set up SSH and Vault

- Add your **public** SSH key to the `authorized_keys` file for each Slurm account. Keep the matching **private** key on your local computer (the inventory currently points to `~/.ssh/id_rsa`). Never copy the private key to Slurm or commit it.
- The inventory already contains Vault-encrypted Google Drive credentials for DVC. From the project root, create `ansible/.vault_pass` with the password used to encrypt those values, then restrict access:

```bash
chmod 600 ansible/.vault_pass
```

Keep this password file private; it is ignored by Git. To encrypt another value, run `cd ansible && ansible-vault encrypt_string --name 'variable_name' --prompt` and put the output in the inventory. The setup playbook writes the encrypted `discord_webhook` inventory variable to `~/.secrets/discord_webhook` on the remote account with private permissions; the notification hooks read the URL from that file. Do not put SSH private keys in Vault.

## 3. Configure targets and projects

Edit `ansible/inventory.yml`. Add Slurm accounts under `slurm.hosts`, setting `ansible_host`, `ansible_user`, and (if needed) `ansible_ssh_private_key_file`. The group values are defaults. Override `repo_name` and `github_repo` on a host when it should use a different project. Use `--limit HOST` to run against one account; omit it to run against all configured accounts.

Check SSH and Ansible access before running the pipeline:

```bash
cd ansible
ansible slurm -m ping
```

## 4. Run the pipeline

Run these from the `ansible` directory:

```bash
ansible-playbook slurm1_setup_tool.yml
ansible-playbook slurm2_fetch_code.yml
ansible-playbook slurm3_fetch_dataset.yml
```

Add `--limit HOST` to a command to target one Slurm account. The setup playbook
installs Git, `uv`, and DVC, clones the project, creates its virtual environment,
and installs packages from `scripts/requirement.txt`. The fetch-code playbook
updates the remote checkout from `main` and can overwrite changes made there.
The dataset playbook runs `dvc pull`; the final playbook runs `slurm/job.sbatch`
with `sbatch` if it contains `#SBATCH` directives, or with `bash` otherwise.
Job output is written under `~/result/running` on Slurm. Image generation can
also be run directly on a regular Linux server with the Bash launchers below.

When using `ansible/sozo_ctl.py`, selecting setup or fetch-code lists the remote repository branches and lets you choose which branch to clone or update. Selecting submit scans `slurm/` for `.sbatch` files and shell scripts. Scripts with `#SBATCH` directives are submitted with `sbatch`; the playbook returns after Slurm accepts the job and sends a Discord submission notification with its job ID, script, host, and working directory. A generated wrapper runs inside the Slurm allocation and sends a second notification when the script exits, including its completion state and a failure alert for a nonzero exit, without keeping Ansible or the terminal open. If the compute node itself is lost, it may be unable to send that final notification. Other shell scripts run through `bash` to completion and send end/failure notifications before Ansible returns. Use `slurm/test_nvidia_smi.sh` as a normal-server test: select it in the submit menu to print the NVIDIA GPU status, if `nvidia-smi` is installed on that host. To enable Discord notifications, put the webhook URL in `~/.secrets/discord_webhook` on the remote account and ensure `curl` is installed; hooks are optional and do not fail the job. Direct playbook runs continue to use `repo_branch` from `ansible/inventory.yml` (default: `main`) and check `slurm/job.sbatch` unless `job_file` is provided.

## 5. Track and transfer data with DVC

Run these from the project root after configuring the DVC remote:

```bash
dvc add datasets/data
git add datasets/data.dvc .gitignore
git commit -m "Track dataset with DVC"
dvc push
```

On another machine, pull the Git changes and run:

```bash
dvc pull
```

The `.dvc` file is committed to Git; the dataset files are stored in the configured DVC remote. The Slurm setup uses the `gdrive` remote and Vault-protected Google credentials.

## 6. Mount the Slurm filesystem locally

Use `ansible/slurm_mount.sh` to mount a Slurm directory locally over SSHFS. Install SSHFS first (`sudo apt install sshfs` on Ubuntu/Debian), then run it from the project root:

```bash
./ansible/slurm_mount.sh mount
./ansible/slurm_mount.sh status
./ansible/slurm_mount.sh unmount
```

When `mount` runs in a terminal, it prompts for the Slurm SSH user, Slurm
host, remote path, and local mount path. Press Enter at a prompt to keep its
displayed default. The current defaults are user
`66070503445@cpe.kmutt.ac.th`, host `portal.slurm.cpe.kmutt.ac.th`, the
remote user's home directory (blank remote path), and `${HOME}/BenSlurm`
locally. The remote path is the directory on Slurm; the local mount path is
where that remote directory appears on your computer. The script creates the
local directory if needed. `status` and `unmount` prompt for the local mount
path so you can target the same mount. For non-interactive runs, set
`SLURM_USER`, `SLURM_HOST`, `REMOTE_PATH`, and `MOUNT_PATH` in the environment;
the SSH key can also be overridden with `SSH_KEY`.

## 7. Generate an inpainted image with Kandinsky 2.2, SDXL, or FLUX.1 Fill

Use Python 3.10 or newer. From the project root, create and activate a virtual
environment and install all generation dependencies. `scripts/requirement.txt`
includes the PyTorch CUDA 12.8 package source and a PyTorch version that supports
the RTX 5080's Blackwell architecture:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r scripts/requirement.txt
```

To check driver visibility and PyTorch CUDA support at any time:

```bash
python scripts/check_gpu.py
nvidia-smi
```

The generator runs the same check automatically before each run that may use
CUDA (`--device auto` or `--device cuda`). `nvidia-smi` seeing a GPU does not
guarantee that PyTorch can use it. Put the source image and a same-sized mask at
`scripts/inputs/image.png` and `scripts/inputs/mask.png`. White mask pixels are
regenerated and black pixels are preserved. Kandinsky requires image dimensions
to be multiples of 64; SDXL requires multiples of 8; FLUX.1 Fill requires
multiples of 16.

Run the generator from the project root. It automatically uses CUDA when
PyTorch reports a usable GPU, with CPU model offload enabled; otherwise it runs
on CPU. Use `--device cuda` to require CUDA or `--device cpu` to force CPU:

```bash
python scripts/inpaint.py \
  --model kandinsky \
  --image scripts/inputs/image.png \
  --mask scripts/inputs/mask.png \
  --prompt "a black cat with glowing eyes, highly detailed" \
  --negative "bad anatomy, deformed, ugly, blurry" \
  --output outputs/inpainted.png \
  --seed 1234
```

Use `--model sdxl` to select Stable Diffusion XL inpainting or `--model
flux-fill` to select FLUX.1 Fill [dev]. Kandinsky remains the default if
`--model` is omitted. Defaults are 50 steps and guidance scale 4.0 for
Kandinsky, 30 and 7.5 for SDXL, and 50 and 30.0 for FLUX.1 Fill. Override them
with `--steps` or `--guidance-scale`. FLUX.1 Fill does not accept a negative
prompt, so omit `--negative` for that model.

For example:

```bash
python scripts/inpaint.py \
  --model flux-fill \
  --image scripts/inputs/image.png \
  --mask scripts/inputs/mask.png \
  --prompt "a black cat with glowing eyes, highly detailed" \
  --output outputs/flux_fill.png \
  --device auto \
  --seed 1234
```

FLUX.1 Fill [dev] is a large (12-billion-parameter) gated model. Accept its
license and configure Hugging Face access before the first download. CUDA runs
use CPU model offload to reduce GPU memory use; they still need substantial
system RAM and GPU memory. The model's license governs how generated outputs
may be used. `scripts/requirement.txt` requires Diffusers 0.32.0 or newer for
`FluxFillPipeline`; reinstall the requirements in your environment to upgrade
an older Diffusers version.

On the first online run, the selected model's checkpoint(s) download from
Hugging Face and are cached locally. Once cached, they can be used offline by
setting `HF_HUB_OFFLINE=1`.

### Run the Kandinsky job

Submit the script from the project root on Slurm:

```bash
sbatch slurm/job_kandinsky.sbatch
```

It preserves the existing Slurm resource profile and uses the Kandinsky
configuration from `slurm/job_kandinsky.sbatch`. Input image, mask, prompt,
output, device, and step count can be overridden with environment variables.
CUDA is checked by the generator automatically when `DEVICE` is `auto` or
`cuda`; `auto` falls back to CPU if PyTorch cannot use the GPU.

```bash
PROMPT="a black cat" \
INPUT_IMAGE="scripts/inputs/image.png" \
MASK_IMAGE="scripts/inputs/mask.png" \
OUTPUT_IMAGE="outputs/cat.png" \
DEVICE=auto \
bash slurm/job_kandinsky.sbatch
```

### Run the FLUX.1 Fill job

From the project root on Slurm, after accepting the model license and running
`hf auth login` on that account:

```bash
sbatch slurm/job_flux.sbatch
```

The job reads `slurm/inputs/image.png` and `slurm/inputs/mask.png` by default,
saves generated images under `slurm/outputs/images/`, and writes Slurm stdout
and stderr logs beside the batch file. Override `INPUT_IMAGE`, `MASK_IMAGE`,
`OUTPUT_IMAGE`, `PROMPT`, `DEVICE`, `STEPS`, or `GUIDANCE_SCALE` when submitting.
It requests 64 GB of system memory and one GPU for CPU-offloaded FLUX inference;
adjust the memory request if the cluster partition imposes a lower limit.

You can also run it directly with Bash for local testing; Slurm directives are
ignored in that case:

```bash
bash slurm/job_flux.sbatch
```
