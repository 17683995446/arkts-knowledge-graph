/**
 * 循环链文件 0
 */

import { ChainClass1 } from './ChainFile1';

export class ChainClass0 {
    next() {
        return new ChainClass1();
    }
}
