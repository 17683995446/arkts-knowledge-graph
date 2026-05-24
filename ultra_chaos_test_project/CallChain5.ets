/**
 * 调用链文件 5
 */

import { ChainClass6 } from './CallChain6';

export class ChainClass5 {
    methodA() {
        const next = new ChainClass6();
        return next.methodB();
    }
    
    methodB() {
        return 'Chain5 B';
    }
    
    methodC() {
        this.methodA();
        this.methodB();
        return 'Chain5 C';
    }
}
