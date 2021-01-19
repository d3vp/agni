package assignment1;

/* config
points = 1
timeout = 7000
*/

import java.time.Duration;
import java.time.Instant;

public class StressTests_TestLargePrime implements Runnable {
    @Override
    public void run() {
        Instant start = Instant.now();
        boolean result = new MyPrimeChecker().isPrime(1073676287L);
        Instant finish = Instant.now();
        if (!result) {
            throw new AssertionError("isPrime() returned incorrect value.");
        }

        long executionTime = Duration.between( start,finish ).toMillis();
        long maxExecutionTime = 1000;
        System.out.printf("isPrime() took %d ms. Maximum allowed time: %d ms%n", executionTime, maxExecutionTime);

        if (executionTime > maxExecutionTime) {
            throw new AssertionError(String.format("isPrime() took longer than expected."));
        }

        System.out.println("Test passed.");
    }
}
