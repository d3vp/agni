package assignment1;

/* config
points = 1
*/

public class IsPrime_ThrowsError implements Runnable {
    @Override
    public void run() {
        boolean result = new MyPrimeChecker().isPrime(null);
        if (result) {
            throw new AssertionError("incorrect value was returned.");
        }
        System.out.println("Test passed.");
    }
}
