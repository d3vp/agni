package assignment1;

/* config
points = 1
*/

public class IsPrime_TestSmall implements Runnable {
    @Override
    public void run() {
        boolean result = new MyPrimeChecker().isPrime(10L);
        if (result) {
            throw new AssertionError("isPrime() returned incorrect value.");
        }
        System.out.println("Test passed.");
    }
}
