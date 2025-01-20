# Track Remote Appfilter

[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/rdehenne/track-remote-appfilter/main.svg)](https://results.pre-commit.ci/latest/github/rdehenne/track-remote-appfilter/main)

A GitHub action to track changes from a remote `appfilter.xml` file and submit changes in a new PR on your repository.
This action is suitable for open source Android icon packs.

## Usage

The recommended way of using this action is through periodic jobs, so that you get notified when the remote `appfilter.xml` changes.

In `.github/workflows`, create a new workflow file, e.g. `action-remote-appfilter.yml`.
Below is a sample workflow file that tracks [Arcticons'](https://github.com/Arcticons-Team/Arcticons/) `appfilter.xml` file:

```
name: Update appfilter from Arcticons

on:
  schedule:
    - cron: '37 15 * * *' # Triggers once a day at 3:37PM GMT, see https://crontab.guru/ for help

jobs:
  track-remote-appfilter:
    runs-on: ubuntu-latest
    steps:
      - name: Track Remote Appfilter
        uses: rdehenne/track-remote-appfilter@v0.0.1-alpha7
        with:
          local-appfilter: 'newicons/appfilter.xml'
          remote-appfilter: 'https://raw.githubusercontent.com/Arcticons-Team/Arcticons/refs/heads/main/newicons/appfilter.xml'
          commit-message: 'Add appfilter items from Arcticons'
          title: 'Add appfilter items from Arcticons'
          body: |
            This PR adds new appfilter items from Arcticons that could be matched to existing drawables.

            See Arcticons' [appfilter.xml](https://github.com/Arcticons-Team/Arcticons/blob/main/newicons/appfilter.xml) for more details.
```

## Action inputs

Two inputs are required: `local-appfilter` and `remote-appfilter`.
Other inputs are optional and come from the [Create Pull Request action](https://github.com/peter-evans/create-pull-request).

| Name                | Description                                                | Default      |
|---------------------|------------------------------------------------------------|--------------|
| `local-appfilter`   | The path to the appfilter.xml in your repository           | **Required** |
| `remote-appfilter`  | The URL to the remote appfilter.xml you want to track[^1]  | **Required** |
| `commit-message`    | The message to use when committing changes. See [commit-message](https://github.com/peter-evans/create-pull-request#commit-message). | `[track-remote-appfilter] Add appfilter items` |
| `title`             | The title of the pull request.                             | `[track-remote-appfilter] Add appfilter items` |
| `body`              | The body of the pull request.                              | `This PR adds new appfilter items from a remote appfilter.xml file that could be matched to existing drawables. Automated changes by the Track Remote Appfilter GitHub action.` |

You can pass any other input used by the Create Pull Request action. Check out [their documentation](https://github.com/peter-evans/create-pull-request) for the full list of inputs available.

[^1]: To get this URL, go to the GitHub repository you want to track. Open the appfilter.xml file on the main branch, click "Raw" and copy-paste the URL.

## License

```
Copyright 2025 Rémi Dehenne

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```
