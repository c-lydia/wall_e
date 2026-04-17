from setuptools import find_packages, setup

package_name = 'feedback'

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
    maintainer='Chheng Lydiya',
    maintainer_email='chhenglydiacl@gmail.com',
    description='Capturing feedback data and process them',
    license='Apache-2.0',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'imu_filter_node = feedback.imu_filter:main',
            'range_filter_node = feedback.range_filter:main',
            'sensor_fusion_node = feedback.sensor_fusion:main'
        ],
    },
)
