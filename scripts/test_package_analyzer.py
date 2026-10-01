"""Check root and nested CMake/Python package discovery through both API paths."""

import os
from package_analyzer import PackageAnalyzer


def test():
    manifests = {
        'package.xml': 'root_package',
        'src/agent_memory_interfaces/package.xml': 'agent_memory_interfaces',
        'src/agent_memory_backend/package.xml': 'agent_memory_backend',
        'workspace/src/agent_memory/package.xml': 'agent_memory',
        'docs/package.xml': 'not_a_package',
        'examples/not-package.xml': 'not_a_manifest',
    }
    paths = set(manifests) | {
        'CMakeLists.txt', 'src/agent_memory_interfaces/CMakeLists.txt',
        'src/agent_memory_backend/setup.py', 'workspace/src/agent_memory/setup.py',
        'examples/CMakeLists.txt',
    }

    class Client:
        def get_repository_tree_paths(self, owner, repo, ref):
            assert (owner, repo, ref) == ('haru-project', 'agent-memory', 'main')
            return paths if self.use_tree else None

        def find_package_xml_files(self, owner, repo, path, ref):
            return [p for p in paths if os.path.basename(p) == 'package.xml']

        def get_repository_contents(self, owner, repo, path, ref):
            return [{'type': 'file', 'name': os.path.basename(p)}
                    for p in paths if os.path.dirname(p) == path]

        def get_file_content(self, owner, repo, path, ref):
            return f'<package><name>{manifests[path]}</name></package>'

    client = Client()
    for client.use_tree in (True, False):
        packages = PackageAnalyzer(client).analyze_repository({
            'owner': {'login': 'haru-project'}, 'name': 'agent-memory',
            'default_branch': 'main',
        })
        assert {p.name for p in packages} == {
            'root_package', 'agent_memory_interfaces',
            'agent_memory_backend', 'agent_memory',
        }
        assert next(p for p in packages if p.name == 'agent_memory_backend').get_rosdep_entries()['noble'] == ['ros-jazzy-agent-memory-backend']
    print('Root and nested CMake/Python package discovery checks passed')


if __name__ == '__main__':
    test()
