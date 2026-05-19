from setuptools import find_packages, setup

with open("requirements.txt") as f:
    install_requires = f.read().strip().split("\n")

setup(
    name="total_vfd",
    version="1.0.0",
    description="Total VFD fiscalisation for ERPNext (Tanzania TRA)",
    author="Total VFD Integration",
    license="MIT",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires,
)
