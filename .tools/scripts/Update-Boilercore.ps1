<#.SYNOPSIS
Update boilercore to the latest commit pin.
#>

git submodule update --init --remote --merge submodules/boilercore
git add --all
git commit --no-verify -m "Update boilercore pinned commit"
git submodule deinit --force submodules/boilercore
git add --all
git commit --no-verify --amend --no-edit
