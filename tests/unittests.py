import time, sys

from stolas.betterui import pprint as print
from common import swap_in, swap_out

def run_test_unit(title, function):
	print("~<s:bright]=> ~<f:blue]{}~<s:reset_all] ".format(title), end = "")
	stdout = swap_out()
	stdout.flush()
	try:
		now = time.time()
		assert(function())
		delta = time.time() - now
	except Exception as err:
		traceback = swap_in(stdout)
		print("~<f:red]~<s:bright]\u2717~<s:reset_all]")
		traceback.seek(0)
		name = "stolas_tucrash_{0}".format(int(time.time()))
		with open(name, "w") as out:
			out.write(traceback.read())
		print("\t=> Traceback written in {}. Aborting!".format(name))
		sys.exit(1)

	swap_in(stdout)
	print("~<f:green]~<s:bright]\u2713~<s:reset_all]\n\tTook {0}s.".format(int(delta)))


def main():
	print("~<s:bright]~) Encoders & Decoders (~~<s:reset_all]")

	from encoders import test_encoders
	run_test_unit("Encoders Test Unit", test_encoders)

	print("~<s:bright]~) Network & Transmission (~~<s:reset_all]")

	from network import test_network_integration_and_collapsing
	run_test_unit("Network Integration", test_network_integration_and_collapsing)

	from transmitters import test_transmission
	run_test_unit("Transmission in a Network", test_transmission)

	print("~<s:bright]~) Message Compression (~~<s:reset_all]")
	from compression import test_compression_advantages
	run_test_unit("Message Compression", (lambda: test_compression_advantages(upperb = 2**20)))

	print("Tests successful")

if __name__ == "__main__":
	main()
