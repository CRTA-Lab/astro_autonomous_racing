from setuptools import find_packages, setup

package_name = 'astro_autonomous_racing'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='istrazivac',
    maintainer_email='luka.siktar11@gmail.com',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'data_preparation = astro_autonomous_racing.data_preparation:main',
            'store_images = astro_autonomous_racing.store_images:main',
            'autonomous_racing_node = astro_autonomous_racing.autonomous_racing:main',
        ],
    },
)
