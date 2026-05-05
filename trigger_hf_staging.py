import git_deploy

target = git_deploy.REPOS["1"] # Staging
git_deploy.deploy(target)
