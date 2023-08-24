<#.SYNOPSIS
Update boilercore to the latest commit pin.
#>

git submodule update --init --remote --merge boilercore
git add --all
git commit -m "Update boilercore pinned commit"
git submodule deinit --force boilercore
git add --all
git commit --amend --no-edit
