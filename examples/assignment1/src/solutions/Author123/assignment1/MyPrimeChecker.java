package assignment1;

public class MyPrimeChecker implements PrimeChecker {
    @Override
    public boolean isPrime(Long x) {
        if (x == 2) {
            return true;
        } else if (x <= 1 || x % 2 == 0) {
            return false;
        }
        for (long n = 3; n < x; n += 2) {
            if (x % n == 0) {
                return false;
            }
        }
        return true;
    }

    public boolean methodWithInfiniteLoop(long x) {
        while (x % 2 == 0) {
            try {
                Thread.sleep(1000);
            } catch (InterruptedException e) {
                e.printStackTrace(System.out);
            }
        }
        return false;
    }
}
