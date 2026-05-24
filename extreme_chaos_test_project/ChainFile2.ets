/**
 * 循环链文件 2
 */

import { ChainClass3 } from './ChainFile3';

export class ChainClass2 {
    next() {
        return new ChainClass3();
    }
}
