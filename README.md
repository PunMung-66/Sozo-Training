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

Keep this password file private; it is ignored by Git. To encrypt another value, run `cd ansible && ansible-vault encrypt_string --name 'variable_name' --prompt` and put the output in the inventory. Do not put SSH private keys in Vault.

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
ansible-playbook slurm4_submit_job.yml
```

Add `--limit HOST` to a command to target one Slurm account. The setup playbook installs Git, `uv`, and DVC and clones the project. The fetch-code playbook updates the remote checkout from `main` and can overwrite changes made there. The dataset playbook runs `dvc pull`; the final playbook submits `slurm/job.sbatch` with `sbatch`. Job output is written under `~/result/running` on Slurm.

When using `ansible/sozo_ctl.py`, selecting setup or fetch-code lists the remote repository branches and lets you choose which branch to clone or update. Direct playbook runs continue to use `repo_branch` from `ansible/inventory.yml` (default: `main`).

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

Use `ansible/slurm_mount.sh` to mount your Slurm home directory locally over SSHFS. Install SSHFS first (`sudo apt install sshfs` on Ubuntu/Debian), then update the Slurm user, host, and local mount path near the top of the script. Run it from the project root:

```bash
./ansible/slurm_mount.sh mount
./ansible/slurm_mount.sh status
./ansible/slurm_mount.sh unmount
```
