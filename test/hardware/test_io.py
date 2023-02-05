import pytest

from silhouette import Graphtec

def generate_stripes(x0, y0, d, l, n = 10):
	y = y0
	pathlist = []
	for i in range(n):
		x = i * d
		pathlist.append([(x, y), (x, y + l)])

	x = x0
	for i in range(n):
		y = i * d
		pathlist.append([(x, y), (x + l, y)])

	return pathlist


def run_task(plotter, d):

	plotter.setup(media = 120,
		speed = 5,
		pressure = 8,
		toolholder = 2, # Head 2
		pen = True,
		trackenhancing=True,
		bladediameter = 0.9,
		landscape = False,
		leftaligned = None,
		depth = 0)
	

	offset = (d, 0.0)
	pathlist = generate_stripes(24.0, 4.0, 0.9, 2.5, n = 4)

	plotter.plot(210.0, 297.0, None, None, pathlist, offset, False, 0, 'start')


def test_resources(do_hw):
	"Test to verify we can re-open the plotter device"
	if not do_hw:
		raise ValueError("""
	Warning: starting hardware test. Please load paper, and insert pen
	in right tool holder (when using dual head devices).
	Then re-run this py.test suite with the --hardware option.
""")

	
	plotter = Graphtec.SilhouetteCameo(umockdev_mode = True)
	run_task(plotter, 0)
	plotter.close()
	# Test re-open:
	plotter = Graphtec.SilhouetteCameo(umockdev_mode = True)
	run_task(plotter, 4.0)


if __name__ == '__main__':
	test_resources(True)
